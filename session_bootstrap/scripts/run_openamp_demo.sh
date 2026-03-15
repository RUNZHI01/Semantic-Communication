#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVER="$PROJECT_ROOT/session_bootstrap/demo/openamp_control_plane_demo/server.py"
SERVER_SUFFIX="/session_bootstrap/demo/openamp_control_plane_demo/server.py"
DEFAULT_HOST="127.0.0.1"
DEFAULT_PORT="8079"
PORT_RECLAIM_WAIT_STEPS=50
PORT_RECLAIM_WAIT_SEC="0.1"

parse_bind_args() {
    local -n host_ref="$1"
    local -n port_ref="$2"
    shift 2

    host_ref="$DEFAULT_HOST"
    port_ref="$DEFAULT_PORT"

    while (($#)); do
        case "$1" in
            --host)
                if (($# >= 2)); then
                    host_ref="$2"
                    shift 2
                    continue
                fi
                break
                ;;
            --host=*)
                host_ref="${1#*=}"
                ;;
            --port)
                if (($# >= 2)); then
                    port_ref="$2"
                    shift 2
                    continue
                fi
                break
                ;;
            --port=*)
                port_ref="${1#*=}"
                ;;
            --)
                break
                ;;
        esac
        shift
    done
}

bind_listener_conflicts() {
    local listener_addr="$1"
    local bind_host="$2"
    local bind_port="$3"

    case "$listener_addr" in
        "*:$bind_port"|0.0.0.0:"$bind_port"|[[]::[]]:"$bind_port"|[[]::ffff:0.0.0.0[]]:"$bind_port")
            return 0
            ;;
    esac

    case "$bind_host" in
        ""|0.0.0.0|::|[::])
            return 0
            ;;
        localhost)
            case "$listener_addr" in
                127.0.0.1:"$bind_port"|localhost:"$bind_port"|[[]::1[]]:"$bind_port")
                    return 0
                    ;;
            esac
            ;;
        127.0.0.1)
            case "$listener_addr" in
                127.0.0.1:"$bind_port"|localhost:"$bind_port")
                    return 0
                    ;;
            esac
            ;;
        ::1|[::1])
            case "$listener_addr" in
                [[]::1[]]:"$bind_port")
                    return 0
                    ;;
            esac
            ;;
        *)
            case "$listener_addr" in
                "$bind_host":"$bind_port"|[[]"$bind_host"[]]:"$bind_port")
                    return 0
                    ;;
            esac
            ;;
    esac

    return 1
}

cmdline_is_demo_server() {
    local cmdline="$1"
    [[ "$cmdline" == *"$SERVER"* ]] || [[ "$cmdline" == *"$SERVER_SUFFIX"* ]]
}

join_listener_addresses() {
    local joined=""
    local record

    for record in "$@"; do
        if [[ -n "$joined" ]]; then
            joined+=", "
        fi
        joined+="${record%%$'\t'*}"
    done

    printf '%s\n' "$joined"
}

list_conflicting_listeners() {
    local line
    local listener_addr

    if ! command -v ss >/dev/null 2>&1; then
        return 0
    fi

    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        listener_addr="$(awk '{print $4}' <<<"$line")"
        [[ -n "$listener_addr" ]] || continue
        if bind_listener_conflicts "$listener_addr" "$REQUESTED_HOST" "$REQUESTED_PORT"; then
            printf '%s\t%s\n' "$listener_addr" "$line"
        fi
    done < <(ss -H -ltn "sport = :$REQUESTED_PORT" 2>/dev/null || true)
}

list_demo_processes_for_requested_bind() {
    local pid
    local cmdline
    local process_host
    local process_port
    local requested_bind_listener
    local -a argv

    case "$REQUESTED_HOST" in
        ""|0.0.0.0|::|[::])
            requested_bind_listener="0.0.0.0:$REQUESTED_PORT"
            ;;
        ::1|[::1])
            requested_bind_listener="[::1]:$REQUESTED_PORT"
            ;;
        *)
            requested_bind_listener="$REQUESTED_HOST:$REQUESTED_PORT"
            ;;
    esac

    while read -r pid cmdline; do
        [[ -n "${pid:-}" && -n "${cmdline:-}" ]] || continue
        cmdline_is_demo_server "$cmdline" || continue

        process_host="$DEFAULT_HOST"
        process_port="$DEFAULT_PORT"
        read -r -a argv <<<"$cmdline"
        parse_bind_args process_host process_port "${argv[@]}"

        if bind_listener_conflicts "$requested_bind_listener" "$process_host" "$process_port"; then
            printf '%s\t%s\t%s\t%s\n' "$pid" "$process_host" "$process_port" "$cmdline"
        fi
    done < <(ps -eo pid=,args=)
}

reclaim_demo_listener_if_safe() {
    local -a conflicting_listeners=()
    local -a demo_processes=()
    local listener_record
    local listener_addr
    local demo_record
    local covered
    local cover_count
    local listener_count
    local other_listener_record
    local pid
    local process_host
    local process_port
    local cmdline
    local listener_summary=""
    local pid_summary=""
    local attempt

    mapfile -t conflicting_listeners < <(list_conflicting_listeners)
    if ((${#conflicting_listeners[@]} == 0)); then
        return 0
    fi

    mapfile -t demo_processes < <(list_demo_processes_for_requested_bind)
    if ((${#demo_processes[@]} == 0)); then
        listener_summary="$(join_listener_addresses "${conflicting_listeners[@]}")"
        printf 'Requested OpenAMP demo port %s is already in use at %s.\n' "$REQUESTED_PORT" "$listener_summary" >&2
        printf 'Refusing to stop a non-OpenAMP listener. Use --port or stop that service manually.\n' >&2
        exit 1
    fi

    for listener_record in "${conflicting_listeners[@]}"; do
        listener_addr="${listener_record%%$'\t'*}"
        covered=1
        cover_count=0
        listener_count=0
        for demo_record in "${demo_processes[@]}"; do
            IFS=$'\t' read -r pid process_host process_port cmdline <<<"$demo_record"
            if bind_listener_conflicts "$listener_addr" "$process_host" "$process_port"; then
                covered=0
                ((cover_count += 1))
            fi
        done
        for other_listener_record in "${conflicting_listeners[@]}"; do
            if [[ "${other_listener_record%%$'\t'*}" == "$listener_addr" ]]; then
                ((listener_count += 1))
            fi
        done
        if ((covered || cover_count < listener_count)); then
            listener_summary="$(join_listener_addresses "${conflicting_listeners[@]}")"
            printf 'Requested OpenAMP demo port %s is already in use at %s.\n' "$REQUESTED_PORT" "$listener_summary" >&2
            printf 'Listener ownership is not clearly limited to %s.\n' "$SERVER" >&2
            printf 'Refusing to kill by port. Use --port or stop the other service manually.\n' >&2
            exit 1
        fi
    done

    for demo_record in "${demo_processes[@]}"; do
        IFS=$'\t' read -r pid process_host process_port cmdline <<<"$demo_record"
        printf 'Reclaiming port %s from existing OpenAMP demo server PID %s.\n' "$REQUESTED_PORT" "$pid" >&2
        kill "$pid" 2>/dev/null || true
        if [[ -n "$pid_summary" ]]; then
            pid_summary+=", "
        fi
        pid_summary+="$pid"
    done

    for ((attempt = 0; attempt < PORT_RECLAIM_WAIT_STEPS; attempt++)); do
        mapfile -t conflicting_listeners < <(list_conflicting_listeners)
        if ((${#conflicting_listeners[@]} == 0)); then
            return 0
        fi
        sleep "$PORT_RECLAIM_WAIT_SEC"
    done

    listener_summary="$(join_listener_addresses "${conflicting_listeners[@]}")"
    printf 'Timed out waiting for existing OpenAMP demo server PID(s) %s to release port %s (%s).\n' "$pid_summary" "$REQUESTED_PORT" "$listener_summary" >&2
    exit 1
}

main() {
    parse_bind_args REQUESTED_HOST REQUESTED_PORT "$@"

    if [[ ! "$REQUESTED_PORT" =~ ^[0-9]+$ ]]; then
        exec python3 "$SERVER" "$@"
    fi

    reclaim_demo_listener_if_safe
    exec python3 "$SERVER" "$@"
}

main "$@"
