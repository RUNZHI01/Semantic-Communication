/*
 * Copyright : (C) 2022 Phytium Information Technology, Inc.
 * All Rights Reserved.
 *
 * This program is OPEN SOURCE software: you can redistribute it and/or modify it
 * under the terms of the Phytium Public License as published by the Phytium Technology Co.,Ltd,
 * either version 1.0 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,but WITHOUT ANY WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Phytium Public License for more details.
 *
 *
 * FilePath: slaver_00_example.c
 * Date: 2022-03-08 22:00:15
 * LastEditTime: 2024-02-27 17:08:19
 * Description:  This is a sample demonstration application that showcases usage of rpmsg
 *  This application is meant to run on the remote CPU running baremetal code.
 *  This application echoes back data that was sent to it by the master core.
 *
 * Modify History:
 *  Ver   Who        Date         Changes
 * ----- ------     --------    --------------------------------------
 * 1.0   huanghe    2022/06/20      first release
 * 1.1   liusm      2024/02/27      fix bug
 * 1.2   liusm      2024/06/07      update for new rpmsg framework
 */

/***************************** Include Files *********************************/

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "sdkconfig.h"
#if defined(CONFIG_USE_MBEDTLS) && !defined(SC_CTRL_USE_MBEDTLS)
#define SC_CTRL_USE_MBEDTLS 1
#endif
#if defined(SC_CTRL_USE_MBEDTLS)
#include <mbedtls/ecdsa.h>
#include <mbedtls/ecp.h>
#include <mbedtls/sha256.h>
#endif
#include <openamp/open_amp.h>
#include <metal/alloc.h>
#include "platform_info.h"
#include "rpmsg_service.h"
#include <metal/sleep.h>
#include "rsc_table.h"
#include "fcache.h"
#include "fdebug.h"
#include "fpsci.h"
#include "platform_info.h"
#include "helper.h"
#include "rpmsg_service.h"
#include "openamp_configs.h"
#include "rsc_table.h"
#include "libmetal_configs.h"
#include "slaver_00_example.h"
/************************** Constant Definitions *****************************/
#define     SLAVE_DEBUG_TAG "    SLAVE_00"
#define     SLAVE_DEBUG_I(format, ...) FT_DEBUG_PRINT_I( SLAVE_DEBUG_TAG, format, ##__VA_ARGS__)
#define     SLAVE_DEBUG_W(format, ...) FT_DEBUG_PRINT_W( SLAVE_DEBUG_TAG, format, ##__VA_ARGS__)
#define     SLAVE_DEBUG_E(format, ...) FT_DEBUG_PRINT_E( SLAVE_DEBUG_TAG, format, ##__VA_ARGS__)

#define SHUTDOWN_MSG                0xEF56A55A
#define SC_CTRL_MAGIC               0x53434F4DU
#define SC_CTRL_VERSION             1U
#define SC_MSG_JOB_REQ              0x0001U
#define SC_MSG_JOB_ACK              0x0002U
#define SC_MSG_HEARTBEAT            0x0003U
#define SC_MSG_HEARTBEAT_ACK        0x0004U
#define SC_MSG_JOB_DONE             0x0005U
#define SC_MSG_SAFE_STOP            0x0007U
#define SC_MSG_STATUS_REQ           0x0008U
#define SC_MSG_STATUS_RESP          0x0009U
#define SC_MSG_SIGNED_ADMISSION_BEGIN      0x000CU
#define SC_MSG_SIGNED_ADMISSION_CHUNK      0x000DU
#define SC_MSG_SIGNED_ADMISSION_SIGNATURE  0x000EU
#define SC_MSG_SIGNED_ADMISSION_COMMIT     0x000FU
#define SC_MSG_SIGNED_ADMISSION_ACK        0x0010U
#define SC_MSG_LINK_HEALTH         0x0060U
#define SC_MSG_MODE_DIRECTIVE      0x0061U
#define SC_MSG_MODE_ACK            0x0062U
#define SC_GUARD_STATE_BOOT         0U
#define SC_GUARD_STATE_READY        1U
#define SC_GUARD_STATE_JOB_ACTIVE   2U
#define SC_GUARD_STATE_WAIT_DONE    3U
#define SC_GUARD_STATE_DENY_PENDING 4U
#define SC_GUARD_STATE_FAULT_LATCHED 5U
#define SC_DECISION_DENY            0U
#define SC_DECISION_ALLOW           1U
#define SC_FAULT_NONE               0U
#define SC_FAULT_ARTIFACT_SHA       1U
#define SC_FAULT_OUTPUT_INCOMPLETE  5U
#define SC_FAULT_DUPLICATE_JOB      8U
#define SC_FAULT_PARAM_RANGE        9U
#define SC_FAULT_MANUAL_SAFE_STOP   10U
#define SC_FAULT_MANIFEST_NOT_STAGED       11U
#define SC_FAULT_MANIFEST_DIGEST_MISMATCH  12U
#define SC_FAULT_MANIFEST_PARSE_ERROR      13U
#define SC_FAULT_SIGNATURE_INVALID         14U
#define SC_FAULT_KEY_SLOT_UNKNOWN          15U
#define SC_FAULT_MANIFEST_CONTRACT_MISMATCH 16U
#define SC_FAULT_LINK_DEGRADED            17U
#define SC_FAULT_LINK_LOST                18U
#define SC_SERVICE_MODE_FULL_FRAME         0U
#define SC_SERVICE_MODE_ROI_ONLY           1U
#define SC_SERVICE_MODE_ALERT_ONLY         2U
#define SC_MODE_REASON_NONE                0U
#define SC_MODE_REASON_SUSTAINED_DEGRADATION 1U
#define SC_MODE_REASON_SUSTAINED_RECOVERY  2U
#define SC_MODE_REASON_BURST_LOSS_EMERGENCY 3U
#define SC_MODE_REASON_LINK_LOST           4U
#define SC_MODE_DEGRADE_THRESHOLD          3U
#define SC_MODE_UPGRADE_THRESHOLD          5U
#define SC_MODE_BURST_LOSS_EMERGENCY       10U
#define SC_MODE_SNR_ROI_THRESHOLD          500U
#define SC_MODE_PER_ROI_THRESHOLD          50U
#define SC_MODE_PER_ALERT_THRESHOLD        200U
#define SC_ADMISSION_TYPE_SIGNED_MANIFEST_V1 1U
#define SC_SIGALG_ECDSA_P256_SHA256_DER      1U
#define SC_SIGNED_MANIFEST_MAX_LEN           1536U
#define SC_SIGNED_SIGNATURE_MAX_LEN          96U
#define SC_SIGNED_MANIFEST_CHUNK_MAX         160U
#define SC_SIGNED_MANIFEST_MAX_CHUNK_COUNT   10U
#define SC_PUBLIC_KEY_UNCOMPRESSED_LEN       65U
#define SC_MANIFEST_SCHEMA_ID_MAX_LEN        32U
#define SC_MANIFEST_ARTIFACT_PATH_MAX_LEN    160U
#define SC_MANIFEST_ARTIFACT_FORMAT_MAX_LEN  48U
#define SC_MANIFEST_VARIANT_MAX_LEN          32U
#define SC_MANIFEST_KEY_ID_MAX_LEN           32U
#define SC_MANIFEST_CHANNEL_MAX_LEN          32U
#define SC_MANIFEST_INPUT_DTYPE_MAX_LEN      16U
#define SC_MANIFEST_CREATED_AT_MAX_LEN       40U
#define SC_MANIFEST_BUILDER_MAX_LEN          64U
#define SC_MANIFEST_SOURCE_REPO_MAX_LEN      64U
#define SC_MANIFEST_SOURCE_GIT_COMMIT_MAX_LEN 64U
#define SC_MANIFEST_NOTE_MAX_LEN             128U
#define SC_SIGNED_STAGE_BEGIN                1U
#define SC_SIGNED_STAGE_CHUNK                2U
#define SC_SIGNED_STAGE_SIGNATURE            3U
#define SC_SIGNED_STAGE_COMMIT               4U
#define SC_SIGNED_ACK_ACCEPTED               0U
#define SC_SIGNED_ACK_DUPLICATE              1U
#define SC_SIGNED_ACK_OUT_OF_RANGE           2U
#define SC_SIGNED_ACK_CRC_ERROR              3U
#define SC_SIGNED_ACK_TOO_LARGE              4U
#define SC_SIGNED_ACK_READY                  5U
/************************** Variable Definitions *****************************/
static volatile int shutdown_req = 0;

/************************** Variable Definitions *****************************/
struct _payload
{
    unsigned long num;
    unsigned long size;
    unsigned char data[];
};

/************************** 资源表定义，与linux协商一致 **********/
static struct remote_resource_table __resource resources __attribute__((used)) = {
	/* Version */
	1,

	/* NUmber of table entries */
	NUM_TABLE_ENTRIES,
	/* reserved fields */
	{0, 0,},

	/* Offsets of rsc entries */
	{
	 offsetof(struct remote_resource_table, rpmsg_vdev),
	},

	/* Virtio device entry */
	{
	 RSC_VDEV, VIRTIO_ID_RPMSG_, VDEV_NOTIFYID, RPMSG_IPU_C0_FEATURES, 0, 0, 0,
	 NUM_VRINGS, {0, 0},
	},
    
	/* Vring rsc entry - part of vdev rsc entry */
	{SLAVE00_TX_VRING_ADDR, VRING_ALIGN, SLAVE00_VRING_NUM, 1, 0},
	{SLAVE00_RX_VRING_ADDR, VRING_ALIGN, SLAVE00_VRING_NUM, 2, 0},
};

/********** 共享内存定义，与linux协商一致 **********/
static metal_phys_addr_t poll_phys_addr = SLAVE00_KICK_IO_ADDR;
struct metal_device kick_driver_00 = {
    .name = SLAVE_00_KICK_DEV_NAME,
	.bus = NULL,
    .num_regions = 1,
	.regions = {
		{
			.virt = (void *)SLAVE00_KICK_IO_ADDR,
			.physmap = &poll_phys_addr,
			.size = 0x1000,
			.page_shift = -1UL,
			.page_mask = -1UL,
			.mem_flags = SLAVE00_SOURCE_TABLE_ATTRIBUTE,
			.ops = {NULL},
		}
	},
    .irq_num = 1,/* Number of IRQs per device */
	.irq_info = (void *)SLAVE_00_SGI,
} ;

struct remoteproc_priv slave_00_priv = {
    .kick_dev_name =           SLAVE_00_KICK_DEV_NAME  ,
	.kick_dev_bus_name =        KICK_BUS_NAME ,
    .cpu_id        =  MASTER_CORE_MASK,/* 给所有core发送中断 */

	.src_table_attribute = SLAVE00_SOURCE_TABLE_ATTRIBUTE ,
	
	/* |rx vring|tx vring|share buffer| */
	.share_mem_va = SLAVE00_SHARE_MEM_ADDR ,
	.share_mem_pa = SLAVE00_SHARE_MEM_ADDR ,
	.share_buffer_offset = SLAVE00_VRING_SIZE ,
	.share_mem_size = SLAVE00_SHARE_MEM_SIZE ,
	.share_mem_attribute = SLAVE00_SHARE_BUFFER_ATTRIBUTE
} ;

/*******************例程全局变量***********************************************/
struct remoteproc remoteproc_slave_00;
static struct rpmsg_device *rpdev_slave_00 = NULL;

typedef struct
{
    uint32_t magic;
    uint16_t version;
    uint16_t msg_type;
    uint32_t seq;
    uint32_t job_id;
    uint32_t payload_len;
    uint32_t header_crc32;
} ScCtrlHdr;

typedef struct
{
    uint8_t expected_sha256[32];
    uint32_t deadline_ms;
    uint32_t expected_outputs;
    uint32_t flags;
} ScJobReq;

typedef struct
{
    uint32_t decision;
    uint32_t fault_code;
    uint32_t guard_state;
} ScJobAck;

typedef struct
{
    uint32_t runtime_state;
    uint32_t elapsed_ms;
    uint32_t completed_outputs;
    uint32_t progress_x100;
} ScHeartbeat;

typedef struct
{
    uint32_t result_code;
    uint32_t output_count;
    uint32_t result_crc32;
    uint32_t reserved;
} ScJobDone;

typedef struct
{
    uint32_t guard_state;
    uint32_t heartbeat_ok;
} ScHeartbeatAck;

typedef struct
{
    uint32_t guard_state;
    uint32_t active_job_id;
    uint32_t last_fault_code;
    uint32_t heartbeat_ok;
    uint32_t sticky_fault;
    uint32_t total_fault_count;
} ScStatusResp;

typedef struct
{
    uint32_t snr_est_db_x100;
    uint32_t per_x1000;
    uint32_t burst_loss_max;
    uint32_t rx_locked;
    uint32_t effective_throughput_kbps;
    uint32_t window_id;
    uint32_t timestamp_ms;
} ScLinkHealth;

typedef struct
{
    uint32_t applied_mode;
    uint32_t allowed_mode;
    uint32_t reason_code;
    uint32_t mode_transitions;
} ScModeDirective;

typedef struct
{
    uint32_t applied_mode;
    uint32_t ack_status;
} ScModeAck;

typedef struct
{
    ScCtrlHdr header;
    ScJobAck payload;
} ScJobAckFrame;

typedef struct
{
    ScCtrlHdr header;
    ScHeartbeatAck payload;
} ScHeartbeatAckFrame;

typedef struct
{
    ScCtrlHdr header;
    ScStatusResp payload;
} ScStatusRespFrame;

typedef struct
{
    ScCtrlHdr header;
    ScModeDirective payload;
} ScModeDirectiveFrame;

typedef struct
{
    uint8_t admission_type;
    uint8_t key_slot;
    uint16_t signature_algorithm;
    uint8_t manifest_sha256[32];
    uint32_t manifest_len;
    uint32_t signature_len;
    uint32_t chunk_size;
} ScSignedAdmissionBeginV1;

typedef struct
{
    uint8_t manifest_sha256[32];
    uint32_t offset;
    uint32_t chunk_len;
    uint32_t chunk_crc32;
} ScSignedAdmissionChunkHdrV1;

typedef struct
{
    uint8_t manifest_sha256[32];
    uint32_t signature_len;
    uint32_t signature_crc32;
} ScSignedAdmissionSignatureHdrV1;

typedef struct
{
    uint8_t manifest_sha256[32];
    uint32_t manifest_crc32;
    uint32_t signature_crc32;
    uint32_t manifest_len;
    uint32_t signature_len;
} ScSignedAdmissionCommitV1;

typedef struct
{
    uint8_t manifest_sha256[32];
    uint32_t stage;
    uint32_t status;
    uint32_t offset;
    uint32_t accepted_len;
} ScSignedAdmissionAckV1;

typedef struct
{
    ScCtrlHdr header;
    ScSignedAdmissionAckV1 payload;
} ScSignedAdmissionAckFrame;

typedef struct
{
    uint32_t job_id;
    uint8_t key_slot;
    uint16_t signature_algorithm;
    uint8_t manifest_sha256[32];
    uint32_t manifest_len;
    uint32_t received_manifest_len;
    uint32_t signature_len;
    uint32_t received_signature_len;
    uint32_t chunk_size;
    uint32_t manifest_crc32;
    uint32_t signature_crc32;
    uint32_t ready_for_job_req;
    uint8_t manifest_buf[SC_SIGNED_MANIFEST_MAX_LEN];
    uint8_t signature_buf[SC_SIGNED_SIGNATURE_MAX_LEN];
} ScSignedAdmissionStage;

typedef struct
{
    const uint8_t *begin;
    uint32_t len;
} ScJsonSlice;

typedef struct
{
    uint8_t slot_id;
    const char *key_id;
    const char *channel;
    uint8_t public_key_uncompressed[SC_PUBLIC_KEY_UNCOMPRESSED_LEN];
} ScPublicKeySlot;

typedef struct
{
    const uint8_t *manifest_bytes;
    uint32_t manifest_len;
    uint8_t manifest_sha256[32];
    const uint8_t *signature_der;
    uint32_t signature_len;
    const uint8_t *public_key_uncompressed;
    uint32_t public_key_len;
} ScEcdsaP256VerifyRequest;

typedef struct
{
    char schema_id[SC_MANIFEST_SCHEMA_ID_MAX_LEN];
    uint32_t manifest_version;
    uint8_t artifact_sha256[32];
    uint32_t artifact_size_bytes;
    char artifact_path[SC_MANIFEST_ARTIFACT_PATH_MAX_LEN];
    char artifact_format[SC_MANIFEST_ARTIFACT_FORMAT_MAX_LEN];
    char artifact_variant[SC_MANIFEST_VARIANT_MAX_LEN];
    uint32_t deadline_ms;
    uint32_t expected_outputs;
    uint32_t flags;
    uint32_t input_shape[4];
    char input_dtype[SC_MANIFEST_INPUT_DTYPE_MAX_LEN];
    char publisher_key_id[SC_MANIFEST_KEY_ID_MAX_LEN];
    char publisher_channel[SC_MANIFEST_CHANNEL_MAX_LEN];
    char provenance_created_at[SC_MANIFEST_CREATED_AT_MAX_LEN];
    char provenance_builder[SC_MANIFEST_BUILDER_MAX_LEN];
    char provenance_source_repo[SC_MANIFEST_SOURCE_REPO_MAX_LEN];
    char provenance_source_git_commit[SC_MANIFEST_SOURCE_GIT_COMMIT_MAX_LEN];
    char provenance_note[SC_MANIFEST_NOTE_MAX_LEN];
} ScManifestContract;

static const uint8_t sc_trusted_sha256[32] = {
    0xbf, 0x25, 0x5c, 0xd4, 0xbb, 0x29, 0x40, 0x8b,
    0x30, 0xb5, 0x0b, 0xce, 0x2a, 0xd8, 0x71, 0x3a,
    0x26, 0x0c, 0x5e, 0x45, 0xef, 0xc2, 0xd0, 0xe8,
    0x31, 0xbd, 0x29, 0x3e, 0xec, 0x9e, 0xde, 0xcb,
};

static uint32_t sc_guard_state = SC_GUARD_STATE_READY;
static uint32_t sc_active_job_id = 0U;
static uint32_t sc_last_fault_code = SC_FAULT_NONE;
static uint32_t sc_total_fault_count = 0U;
static uint32_t sc_heartbeat_seen = 0U;
static uint32_t sc_expected_outputs = 0U;
static uint32_t sc_allowed_mode = SC_SERVICE_MODE_FULL_FRAME;
static uint32_t sc_current_mode = SC_SERVICE_MODE_FULL_FRAME;
static uint32_t sc_mode_transition_count = 0U;
static uint32_t sc_mode_degrade_window_count = 0U;
static uint32_t sc_mode_upgrade_window_count = 0U;
static uint32_t sc_last_mode_reason = SC_MODE_REASON_NONE;
static ScSignedAdmissionStage sc_signed_stage;
static const ScPublicKeySlot sc_public_key_slots[] = {
    {
        1U,
        "mean4-v7-dev-20260420",
        "openamp-demo-current",
        {
            0x04U, 0x38U, 0xFDU, 0x2BU, 0x13U, 0x7AU, 0x99U, 0x43U,
            0x2FU, 0x66U, 0xF4U, 0xECU, 0x76U, 0x63U, 0x43U, 0x4BU,
            0xA6U, 0xF2U, 0x3DU, 0xBAU, 0x56U, 0xD9U, 0x1EU, 0xF5U,
            0x52U, 0xB1U, 0x77U, 0xEFU, 0x2CU, 0xECU, 0x51U, 0xC4U,
            0xA7U, 0xA7U, 0x64U, 0x36U, 0xAFU, 0x4CU, 0xDBU, 0x67U,
            0x01U, 0xA4U, 0x71U, 0x6EU, 0x83U, 0x7AU, 0xB1U, 0x52U,
            0x0BU, 0x14U, 0xBAU, 0x9EU, 0xEAU, 0x7CU, 0xF0U, 0x6CU,
            0x9EU, 0x25U, 0x92U, 0xFCU, 0xC2U, 0x08U, 0x99U, 0x9CU,
            0x1CU,
        },
    },
};
/************************** Function Prototypes ******************************/
static int sc_ctrl_has_admitted_job(void)
{
    return ((sc_guard_state == SC_GUARD_STATE_JOB_ACTIVE) &&
            (sc_active_job_id != 0U));
}

static void sc_ctrl_reset_service_mode_state(void)
{
    sc_allowed_mode = SC_SERVICE_MODE_FULL_FRAME;
    sc_current_mode = SC_SERVICE_MODE_FULL_FRAME;
    sc_mode_transition_count = 0U;
    sc_mode_degrade_window_count = 0U;
    sc_mode_upgrade_window_count = 0U;
    sc_last_mode_reason = SC_MODE_REASON_NONE;
}

static void sc_ctrl_clear_active_job(void)
{
    sc_guard_state = SC_GUARD_STATE_READY;
    sc_active_job_id = 0U;
    sc_heartbeat_seen = 0U;
    sc_expected_outputs = 0U;
    sc_ctrl_reset_service_mode_state();
}

static void sc_ctrl_clear_signed_stage(void)
{
    memset(&sc_signed_stage, 0, sizeof(sc_signed_stage));
}

static int sc_ctrl_is_signed_stage_for_job(uint32_t job_id)
{
    return ((sc_signed_stage.job_id == job_id) &&
            (sc_signed_stage.manifest_len != 0U));
}

static void sc_ctrl_reset_runtime_state(void)
{
    sc_ctrl_clear_active_job();
    sc_ctrl_clear_signed_stage();
    sc_last_fault_code = SC_FAULT_NONE;
    sc_total_fault_count = 0U;
}

static void sc_ctrl_normalize_runtime_state(void)
{
    if (!sc_ctrl_has_admitted_job())
    {
        sc_ctrl_clear_active_job();
    }
}

static uint32_t sc_ctrl_crc32(const void *data, size_t len)
{
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t crc = 0xFFFFFFFFU;
    size_t byte_index;
    unsigned int bit_index;

    for (byte_index = 0; byte_index < len; ++byte_index)
    {
        crc ^= (uint32_t)bytes[byte_index];
        for (bit_index = 0; bit_index < 8U; ++bit_index)
        {
            if (crc & 1U)
            {
                crc = (crc >> 1) ^ 0xEDB88320U;
            }
            else
            {
                crc >>= 1;
            }
        }
    }

    return crc ^ 0xFFFFFFFFU;
}

static uint32_t sc_ctrl_compute_header_crc(const ScCtrlHdr *header)
{
    return sc_ctrl_crc32(header, 20U);
}

static void sc_ctrl_note_fault(uint32_t fault_code)
{
    sc_last_fault_code = fault_code;
    if (fault_code != SC_FAULT_NONE)
    {
        sc_total_fault_count += 1U;
    }
}

static int sc_ctrl_parse_header(const void *data, size_t len, ScCtrlHdr *header)
{
    if (len < sizeof(*header))
    {
        return -1;
    }

    memcpy(header, data, sizeof(*header));

    if (header->magic != SC_CTRL_MAGIC)
    {
        return -2;
    }

    if (header->version != SC_CTRL_VERSION)
    {
        return -3;
    }

    if ((size_t)header->payload_len != (len - sizeof(*header)))
    {
        return -4;
    }

    if (sc_ctrl_compute_header_crc(header) != header->header_crc32)
    {
        return -5;
    }

    return 0;
}

static int sc_ctrl_is_known_flag(uint32_t flags)
{
    return (flags == 1U) || (flags == 2U) || (flags == 3U);
}

static int sc_ctrl_lookup_public_key_slot(uint8_t key_slot,
                                          const ScPublicKeySlot **out_slot)
{
    size_t entry_index;

    for (entry_index = 0U;
         entry_index < (sizeof(sc_public_key_slots) / sizeof(sc_public_key_slots[0]));
         ++entry_index)
    {
        const ScPublicKeySlot *entry = &sc_public_key_slots[entry_index];

        if ((entry->slot_id == key_slot) &&
            (entry->key_id != NULL) &&
            (entry->channel != NULL))
        {
            if (out_slot != NULL)
            {
                *out_slot = entry;
            }
            return 1;
        }
    }

    if (out_slot != NULL)
    {
        *out_slot = NULL;
    }
    return 0;
}

static int sc_ctrl_send_signed_admission_ack(struct rpmsg_endpoint *ept, uint32_t src,
                                             const ScCtrlHdr *request_header,
                                             const uint8_t manifest_sha256[32],
                                             uint32_t stage, uint32_t status,
                                             uint32_t offset, uint32_t accepted_len)
{
    ScSignedAdmissionAckFrame response;

    memset(&response, 0, sizeof(response));
    ept->dest_addr = src;
    response.header.magic = SC_CTRL_MAGIC;
    response.header.version = SC_CTRL_VERSION;
    response.header.msg_type = SC_MSG_SIGNED_ADMISSION_ACK;
    response.header.seq = request_header->seq;
    response.header.job_id = request_header->job_id;
    response.header.payload_len = sizeof(response.payload);
    response.header.header_crc32 = sc_ctrl_compute_header_crc(&response.header);
    if (manifest_sha256 != NULL)
    {
        memcpy(response.payload.manifest_sha256, manifest_sha256,
               sizeof(response.payload.manifest_sha256));
    }
    response.payload.stage = stage;
    response.payload.status = status;
    response.payload.offset = offset;
    response.payload.accepted_len = accepted_len;

    return rpmsg_send(ept, &response, sizeof(response));
}

static int sc_ctrl_handle_signed_admission_begin(struct rpmsg_endpoint *ept, uint32_t src,
                                                 const ScCtrlHdr *request_header,
                                                 const void *payload_data)
{
    ScSignedAdmissionBeginV1 request;
    uint8_t zero_sha256[32] = {0};
    uint32_t chunk_count = 0U;

    if (request_header->payload_len != sizeof(request))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 zero_sha256,
                                                 SC_SIGNED_STAGE_BEGIN,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    memcpy(&request, payload_data, sizeof(request));
    if ((request.admission_type != SC_ADMISSION_TYPE_SIGNED_MANIFEST_V1) ||
        (request.signature_algorithm != SC_SIGALG_ECDSA_P256_SHA256_DER))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_BEGIN,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if ((request.manifest_len == 0U) ||
        (request.manifest_len > SC_SIGNED_MANIFEST_MAX_LEN) ||
        (request.signature_len == 0U) ||
        (request.signature_len > SC_SIGNED_SIGNATURE_MAX_LEN) ||
        (request.chunk_size == 0U) ||
        (request.chunk_size > SC_SIGNED_MANIFEST_CHUNK_MAX))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_BEGIN,
                                                 SC_SIGNED_ACK_TOO_LARGE,
                                                 0U, 0U);
    }

    chunk_count = (request.manifest_len + request.chunk_size - 1U) / request.chunk_size;
    if (chunk_count > SC_SIGNED_MANIFEST_MAX_CHUNK_COUNT)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_BEGIN,
                                                 SC_SIGNED_ACK_TOO_LARGE,
                                                 0U, 0U);
    }

    if (sc_ctrl_is_signed_stage_for_job(request_header->job_id) &&
        (memcmp(sc_signed_stage.manifest_sha256, request.manifest_sha256,
                sizeof(request.manifest_sha256)) == 0) &&
        (sc_signed_stage.manifest_len == request.manifest_len) &&
        (sc_signed_stage.signature_len == request.signature_len) &&
        (sc_signed_stage.chunk_size == request.chunk_size))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_BEGIN,
                                                 SC_SIGNED_ACK_DUPLICATE,
                                                 0U,
                                                 request.manifest_len);
    }

    sc_ctrl_clear_signed_stage();
    sc_signed_stage.job_id = request_header->job_id;
    sc_signed_stage.key_slot = request.key_slot;
    sc_signed_stage.signature_algorithm = request.signature_algorithm;
    memcpy(sc_signed_stage.manifest_sha256, request.manifest_sha256,
           sizeof(sc_signed_stage.manifest_sha256));
    sc_signed_stage.manifest_len = request.manifest_len;
    sc_signed_stage.signature_len = request.signature_len;
    sc_signed_stage.chunk_size = request.chunk_size;

    return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                             request.manifest_sha256,
                                             SC_SIGNED_STAGE_BEGIN,
                                             SC_SIGNED_ACK_ACCEPTED,
                                             0U,
                                             request.manifest_len);
}

static int sc_ctrl_handle_signed_admission_chunk(struct rpmsg_endpoint *ept, uint32_t src,
                                                 const ScCtrlHdr *request_header,
                                                 const void *payload_data)
{
    ScSignedAdmissionChunkHdrV1 request;
    const uint8_t *chunk_data;
    uint8_t zero_sha256[32] = {0};

    if (!sc_ctrl_is_signed_stage_for_job(request_header->job_id))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 zero_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if (request_header->payload_len < sizeof(request))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 sc_signed_stage.manifest_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    memcpy(&request, payload_data, sizeof(request));
    if (memcmp(request.manifest_sha256, sc_signed_stage.manifest_sha256,
               sizeof(request.manifest_sha256)) != 0)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 request.offset, 0U);
    }

    if ((request.chunk_len == 0U) ||
        (request.chunk_len > sc_signed_stage.chunk_size) ||
        (request_header->payload_len != (sizeof(request) + request.chunk_len)) ||
        ((request.offset + request.chunk_len) > sc_signed_stage.manifest_len))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 request.offset, 0U);
    }

    chunk_data = ((const uint8_t *)payload_data) + sizeof(request);
    if ((request.offset + request.chunk_len) <= sc_signed_stage.received_manifest_len)
    {
        if (memcmp(sc_signed_stage.manifest_buf + request.offset,
                   chunk_data, request.chunk_len) == 0)
        {
            return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                     request.manifest_sha256,
                                                     SC_SIGNED_STAGE_CHUNK,
                                                     SC_SIGNED_ACK_DUPLICATE,
                                                     request.offset,
                                                     request.chunk_len);
        }
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 request.offset, 0U);
    }

    if (request.offset != sc_signed_stage.received_manifest_len)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 request.offset, 0U);
    }

    if (sc_ctrl_crc32(chunk_data, request.chunk_len) != request.chunk_crc32)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_CHUNK,
                                                 SC_SIGNED_ACK_CRC_ERROR,
                                                 request.offset, 0U);
    }

    memcpy(sc_signed_stage.manifest_buf + request.offset, chunk_data, request.chunk_len);
    sc_signed_stage.received_manifest_len += request.chunk_len;
    return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                             request.manifest_sha256,
                                             SC_SIGNED_STAGE_CHUNK,
                                             SC_SIGNED_ACK_ACCEPTED,
                                             request.offset,
                                             request.chunk_len);
}

static int sc_ctrl_handle_signed_admission_signature(struct rpmsg_endpoint *ept, uint32_t src,
                                                     const ScCtrlHdr *request_header,
                                                     const void *payload_data)
{
    ScSignedAdmissionSignatureHdrV1 request;
    const uint8_t *signature_data;
    uint8_t zero_sha256[32] = {0};

    if (!sc_ctrl_is_signed_stage_for_job(request_header->job_id))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 zero_sha256,
                                                 SC_SIGNED_STAGE_SIGNATURE,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if (request_header->payload_len < sizeof(request))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 sc_signed_stage.manifest_sha256,
                                                 SC_SIGNED_STAGE_SIGNATURE,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    memcpy(&request, payload_data, sizeof(request));
    if (memcmp(request.manifest_sha256, sc_signed_stage.manifest_sha256,
               sizeof(request.manifest_sha256)) != 0)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_SIGNATURE,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if ((request.signature_len == 0U) ||
        (request.signature_len > SC_SIGNED_SIGNATURE_MAX_LEN) ||
        (request.signature_len != sc_signed_stage.signature_len) ||
        (request_header->payload_len != (sizeof(request) + request.signature_len)))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_SIGNATURE,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    signature_data = ((const uint8_t *)payload_data) + sizeof(request);
    if ((sc_signed_stage.received_signature_len == request.signature_len) &&
        (memcmp(sc_signed_stage.signature_buf, signature_data, request.signature_len) == 0))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_SIGNATURE,
                                                 SC_SIGNED_ACK_DUPLICATE,
                                                 0U, request.signature_len);
    }

    if (sc_ctrl_crc32(signature_data, request.signature_len) != request.signature_crc32)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_SIGNATURE,
                                                 SC_SIGNED_ACK_CRC_ERROR,
                                                 0U, 0U);
    }

    memcpy(sc_signed_stage.signature_buf, signature_data, request.signature_len);
    sc_signed_stage.received_signature_len = request.signature_len;
    return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                             request.manifest_sha256,
                                             SC_SIGNED_STAGE_SIGNATURE,
                                             SC_SIGNED_ACK_ACCEPTED,
                                             0U, request.signature_len);
}

static int sc_ctrl_handle_signed_admission_commit(struct rpmsg_endpoint *ept, uint32_t src,
                                                  const ScCtrlHdr *request_header,
                                                  const void *payload_data)
{
    ScSignedAdmissionCommitV1 request;
    uint8_t zero_sha256[32] = {0};

    if (!sc_ctrl_is_signed_stage_for_job(request_header->job_id))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 zero_sha256,
                                                 SC_SIGNED_STAGE_COMMIT,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if (request_header->payload_len != sizeof(request))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 sc_signed_stage.manifest_sha256,
                                                 SC_SIGNED_STAGE_COMMIT,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    memcpy(&request, payload_data, sizeof(request));
    if (memcmp(request.manifest_sha256, sc_signed_stage.manifest_sha256,
               sizeof(request.manifest_sha256)) != 0)
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_COMMIT,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if ((request.manifest_len != sc_signed_stage.manifest_len) ||
        (request.signature_len != sc_signed_stage.signature_len) ||
        (sc_signed_stage.received_manifest_len != sc_signed_stage.manifest_len) ||
        (sc_signed_stage.received_signature_len != sc_signed_stage.signature_len))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_COMMIT,
                                                 SC_SIGNED_ACK_OUT_OF_RANGE,
                                                 0U, 0U);
    }

    if ((sc_ctrl_crc32(sc_signed_stage.manifest_buf, sc_signed_stage.manifest_len) !=
         request.manifest_crc32) ||
        (sc_ctrl_crc32(sc_signed_stage.signature_buf, sc_signed_stage.signature_len) !=
         request.signature_crc32))
    {
        return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                                 request.manifest_sha256,
                                                 SC_SIGNED_STAGE_COMMIT,
                                                 SC_SIGNED_ACK_CRC_ERROR,
                                                 0U, 0U);
    }

    sc_signed_stage.manifest_crc32 = request.manifest_crc32;
    sc_signed_stage.signature_crc32 = request.signature_crc32;
    sc_signed_stage.ready_for_job_req = 1U;
    return sc_ctrl_send_signed_admission_ack(ept, src, request_header,
                                             request.manifest_sha256,
                                             SC_SIGNED_STAGE_COMMIT,
                                             SC_SIGNED_ACK_READY,
                                             0U,
                                             request.manifest_len);
}

static int sc_ctrl_parse_hex_nibble(uint8_t raw, uint8_t *out_nibble)
{
    if ((raw >= (uint8_t)'0') && (raw <= (uint8_t)'9'))
    {
        *out_nibble = (uint8_t)(raw - (uint8_t)'0');
        return 1;
    }
    if ((raw >= (uint8_t)'a') && (raw <= (uint8_t)'f'))
    {
        *out_nibble = (uint8_t)(raw - (uint8_t)'a' + 10U);
        return 1;
    }
    if ((raw >= (uint8_t)'A') && (raw <= (uint8_t)'F'))
    {
        *out_nibble = (uint8_t)(raw - (uint8_t)'A' + 10U);
        return 1;
    }
    return 0;
}

static int sc_ctrl_parse_sha256_hex(const char *text, uint8_t out_sha256[32])
{
    uint32_t index;

    if ((text == NULL) || (out_sha256 == NULL) || (strlen(text) != 64U))
    {
        return 0;
    }
    for (index = 0U; index < 32U; ++index)
    {
        uint8_t high = 0U;
        uint8_t low = 0U;

        if (!sc_ctrl_parse_hex_nibble((uint8_t)text[index * 2U], &high) ||
            !sc_ctrl_parse_hex_nibble((uint8_t)text[index * 2U + 1U], &low))
        {
            return 0;
        }
        out_sha256[index] = (uint8_t)((high << 4U) | low);
    }
    return 1;
}

static int sc_ctrl_manifest_flag_from_string(const char *text, uint32_t *out_flags)
{
    if ((text == NULL) || (out_flags == NULL))
    {
        return 0;
    }
    if (strcmp(text, "payload") == 0)
    {
        *out_flags = 1U;
        return 1;
    }
    if (strcmp(text, "reconstruction") == 0)
    {
        *out_flags = 2U;
        return 1;
    }
    if (strcmp(text, "smoke") == 0)
    {
        *out_flags = 3U;
        return 1;
    }
    return 0;
}

static const uint8_t *sc_ctrl_json_skip_ws(const uint8_t *cursor, const uint8_t *json_end)
{
    while ((cursor < json_end) &&
           ((*cursor == (uint8_t)' ') ||
            (*cursor == (uint8_t)'\n') ||
            (*cursor == (uint8_t)'\r') ||
            (*cursor == (uint8_t)'\t')))
    {
        ++cursor;
    }
    return cursor;
}

static int sc_ctrl_json_build_key_token(const char *field_name,
                                        char *out_token,
                                        uint32_t out_token_len,
                                        uint32_t *out_written_len)
{
    size_t field_name_len;

    if ((field_name == NULL) || (out_token == NULL))
    {
        return 0;
    }
    field_name_len = strlen(field_name);
    if ((field_name_len + 3U) > out_token_len)
    {
        return 0;
    }
    out_token[0] = '"';
    memcpy(&out_token[1], field_name, field_name_len);
    out_token[field_name_len + 1U] = '"';
    out_token[field_name_len + 2U] = ':';
    if (out_written_len != NULL)
    {
        *out_written_len = (uint32_t)(field_name_len + 3U);
    }
    return 1;
}

static int sc_ctrl_json_find_key_start(const uint8_t *json_bytes,
                                       uint32_t json_len,
                                       const char *field_name,
                                       const uint8_t **out_value_start)
{
    char token[48];
    uint32_t token_len = 0U;
    uint32_t index;
    uint32_t object_depth = 0U;
    int in_string = 0;
    const uint8_t *json_end = NULL;

    if ((json_bytes == NULL) || (field_name == NULL) || (out_value_start == NULL))
    {
        return 0;
    }
    if (!sc_ctrl_json_build_key_token(field_name, token, sizeof(token), &token_len))
    {
        return 0;
    }
    json_end = json_bytes + json_len;
    for (index = 0U; index + token_len <= json_len; ++index)
    {
        uint8_t ch = json_bytes[index];

        if (in_string)
        {
            if (ch == (uint8_t)'\\')
            {
                return 0;
            }
            if (ch == (uint8_t)'"')
            {
                in_string = 0;
            }
            continue;
        }
        if (ch == (uint8_t)'"')
        {
            if ((object_depth == 1U) &&
                (memcmp(&json_bytes[index], token, token_len) == 0))
            {
                const uint8_t *value_cursor = &json_bytes[index + token_len];

                value_cursor = sc_ctrl_json_skip_ws(value_cursor, json_end);
                if (value_cursor >= json_end)
                {
                    return 0;
                }
                *out_value_start = value_cursor;
                return 1;
            }
            in_string = 1;
            continue;
        }
        if (ch == (uint8_t)'{')
        {
            ++object_depth;
        }
        else if (ch == (uint8_t)'}')
        {
            if (object_depth == 0U)
            {
                return 0;
            }
            --object_depth;
        }
    }
    return 0;
}

static int sc_ctrl_json_find_object(const uint8_t *json_bytes,
                                    uint32_t json_len,
                                    const char *field_name,
                                    ScJsonSlice *out_object)
{
    const uint8_t *value_start = NULL;
    const uint8_t *cursor;
    uint32_t depth = 0U;
    int in_string = 0;

    if ((out_object == NULL) ||
        !sc_ctrl_json_find_key_start(json_bytes, json_len, field_name, &value_start) ||
        (value_start[0] != (uint8_t)'{'))
    {
        return 0;
    }
    cursor = value_start;
    while ((uint32_t)(cursor - json_bytes) < json_len)
    {
        uint8_t ch = *cursor;

        if (in_string)
        {
            if (ch == (uint8_t)'\\')
            {
                return 0;
            }
            if (ch == (uint8_t)'"')
            {
                in_string = 0;
            }
        }
        else if (ch == (uint8_t)'"')
        {
            in_string = 1;
        }
        else if (ch == (uint8_t)'{')
        {
            ++depth;
        }
        else if (ch == (uint8_t)'}')
        {
            if (depth == 0U)
            {
                return 0;
            }
            --depth;
            if (depth == 0U)
            {
                out_object->begin = value_start;
                out_object->len = (uint32_t)((cursor - value_start) + 1U);
                return 1;
            }
        }
        ++cursor;
    }
    return 0;
}

static int sc_ctrl_json_find_string_field(const uint8_t *json_bytes,
                                          uint32_t json_len,
                                          const char *field_name,
                                          char *out_text,
                                          uint32_t out_text_len)
{
    const uint8_t *value_start = NULL;
    const uint8_t *cursor;
    uint32_t text_len = 0U;

    if ((out_text == NULL) ||
        !sc_ctrl_json_find_key_start(json_bytes, json_len, field_name, &value_start) ||
        (value_start[0] != (uint8_t)'"'))
    {
        return 0;
    }
    cursor = &value_start[1];
    while ((uint32_t)(cursor - json_bytes) < json_len)
    {
        if (*cursor == (uint8_t)'\\')
        {
            return 0;
        }
        if (*cursor == (uint8_t)'"')
        {
            break;
        }
        ++cursor;
        ++text_len;
    }
    if (((uint32_t)(cursor - json_bytes) >= json_len) ||
        ((text_len + 1U) > out_text_len))
    {
        return 0;
    }
    memcpy(out_text, &value_start[1], text_len);
    out_text[text_len] = '\0';
    return 1;
}

static int sc_ctrl_json_find_u32_field(const uint8_t *json_bytes,
                                       uint32_t json_len,
                                       const char *field_name,
                                       uint32_t *out_value)
{
    const uint8_t *value_start = NULL;
    const uint8_t *cursor;
    uint32_t value = 0U;
    uint32_t digit_count = 0U;

    if ((out_value == NULL) ||
        !sc_ctrl_json_find_key_start(json_bytes, json_len, field_name, &value_start))
    {
        return 0;
    }
    cursor = value_start;
    while ((uint32_t)(cursor - json_bytes) < json_len)
    {
        uint8_t ch = *cursor;

        if ((ch < (uint8_t)'0') || (ch > (uint8_t)'9'))
        {
            break;
        }
        if ((value > 429496729U) ||
            ((value == 429496729U) && ((uint32_t)(ch - (uint8_t)'0') > 5U)))
        {
            return 0;
        }
        value = (value * 10U) + (uint32_t)(ch - (uint8_t)'0');
        ++digit_count;
        ++cursor;
    }
    if (digit_count == 0U)
    {
        return 0;
    }
    *out_value = value;
    return 1;
}

static int sc_ctrl_json_find_optional_string_field(const uint8_t *json_bytes,
                                                   uint32_t json_len,
                                                   const char *field_name,
                                                   char *out_text,
                                                   uint32_t out_text_len)
{
    const uint8_t *value_start = NULL;

    if ((out_text == NULL) || (out_text_len == 0U))
    {
        return 0;
    }
    out_text[0] = '\0';
    if (!sc_ctrl_json_find_key_start(json_bytes, json_len, field_name, &value_start))
    {
        return 1;
    }
    if (value_start[0] != (uint8_t)'"')
    {
        return 0;
    }
    return sc_ctrl_json_find_string_field(json_bytes, json_len, field_name,
                                          out_text, out_text_len);
}

static int sc_ctrl_json_find_u32_array4_field(const uint8_t *json_bytes,
                                              uint32_t json_len,
                                              const char *field_name,
                                              uint32_t out_values[4])
{
    const uint8_t *value_start = NULL;
    const uint8_t *cursor;
    uint32_t value_index = 0U;

    if ((out_values == NULL) ||
        !sc_ctrl_json_find_key_start(json_bytes, json_len, field_name, &value_start) ||
        (value_start[0] != (uint8_t)'['))
    {
        return 0;
    }
    cursor = &value_start[1];
    while ((uint32_t)(cursor - json_bytes) < json_len)
    {
        uint8_t ch = *cursor;
        uint32_t value = 0U;
        uint32_t digit_count = 0U;

        if ((ch == (uint8_t)' ') || (ch == (uint8_t)'\n') ||
            (ch == (uint8_t)'\r') || (ch == (uint8_t)'\t') ||
            (ch == (uint8_t)','))
        {
            ++cursor;
            continue;
        }
        if (ch == (uint8_t)']')
        {
            return (value_index == 4U);
        }
        if (value_index >= 4U)
        {
            return 0;
        }
        while ((uint32_t)(cursor - json_bytes) < json_len)
        {
            ch = *cursor;
            if ((ch < (uint8_t)'0') || (ch > (uint8_t)'9'))
            {
                break;
            }
            if ((value > 429496729U) ||
                ((value == 429496729U) && ((uint32_t)(ch - (uint8_t)'0') > 5U)))
            {
                return 0;
            }
            value = (value * 10U) + (uint32_t)(ch - (uint8_t)'0');
            ++digit_count;
            ++cursor;
        }
        if (digit_count == 0U)
        {
            return 0;
        }
        out_values[value_index] = value;
        ++value_index;
    }
    return 0;
}

static int sc_ctrl_json_expect_string_field(const uint8_t *json_bytes,
                                            uint32_t json_len,
                                            const char *field_name,
                                            const char *expected_text,
                                            char *out_text,
                                            uint32_t out_text_len)
{
    if (!sc_ctrl_json_find_string_field(json_bytes, json_len, field_name,
                                        out_text, out_text_len))
    {
        return 0;
    }
    if ((expected_text != NULL) && (strcmp(out_text, expected_text) != 0))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_json_expect_u32_field(const uint8_t *json_bytes,
                                         uint32_t json_len,
                                         const char *field_name,
                                         uint32_t expected_value,
                                         uint32_t *out_value)
{
    if (!sc_ctrl_json_find_u32_field(json_bytes, json_len, field_name, out_value) ||
        (*out_value != expected_value))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_crypto_sha256(const uint8_t *input,
                                 uint32_t input_len,
                                 uint8_t out_digest[32])
{
    int sdk_status = -1;

    if ((input == NULL) || (input_len == 0U) || (out_digest == NULL))
    {
        return 0;
    }
#if defined(SC_CTRL_USE_MBEDTLS)
    sdk_status = mbedtls_sha256(input, input_len, out_digest, 0);
    return (sdk_status == 0);
#else
    (void)sdk_status;
    return 0;
#endif
}

static int sc_ctrl_crypto_verify_request_is_valid(const ScEcdsaP256VerifyRequest *request)
{
    if ((request == NULL) || (request->manifest_bytes == NULL) ||
        (request->manifest_len == 0U) || (request->signature_der == NULL) ||
        (request->signature_len == 0U) ||
        (request->signature_len > SC_SIGNED_SIGNATURE_MAX_LEN) ||
        (request->public_key_uncompressed == NULL) ||
        (request->public_key_len != SC_PUBLIC_KEY_UNCOMPRESSED_LEN))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_crypto_verify_ecdsa_p256_sha256_der(
    const ScEcdsaP256VerifyRequest *request)
{
    int sdk_status = -1;

    if (!sc_ctrl_crypto_verify_request_is_valid(request))
    {
        return 0;
    }
#if defined(SC_CTRL_USE_MBEDTLS)
    mbedtls_ecdsa_context ecdsa;

    mbedtls_ecdsa_init(&ecdsa);
    sdk_status = mbedtls_ecp_group_load(&ecdsa.grp, MBEDTLS_ECP_DP_SECP256R1);
    if (sdk_status == 0)
    {
        sdk_status = mbedtls_ecp_point_read_binary(&ecdsa.grp,
                                                   &ecdsa.Q,
                                                   request->public_key_uncompressed,
                                                   request->public_key_len);
    }
    if (sdk_status == 0)
    {
        sdk_status = mbedtls_ecp_check_pubkey(&ecdsa.grp, &ecdsa.Q);
    }
    if (sdk_status == 0)
    {
        sdk_status = mbedtls_ecdsa_read_signature(&ecdsa,
                                                  request->manifest_sha256,
                                                  sizeof(request->manifest_sha256),
                                                  request->signature_der,
                                                  request->signature_len);
    }
    mbedtls_ecdsa_free(&ecdsa);
    return (sdk_status == 0);
#else
    (void)request->manifest_bytes;
    (void)request->manifest_len;
    (void)sdk_status;
    return 0;
#endif
}

static int sc_ctrl_verify_manifest_signature(const ScPublicKeySlot *slot,
                                             const uint8_t expected_manifest_sha256[32],
                                             const uint8_t *manifest_bytes,
                                             uint32_t manifest_len,
                                             const uint8_t *signature_bytes,
                                             uint32_t signature_len)
{
    uint8_t manifest_sha256[32];
    ScEcdsaP256VerifyRequest verify_request;

    if ((slot == NULL) || (expected_manifest_sha256 == NULL) ||
        (manifest_bytes == NULL) || (manifest_len == 0U) ||
        (signature_bytes == NULL) || (signature_len == 0U))
    {
        return 0;
    }
    if (!sc_ctrl_crypto_sha256(manifest_bytes, manifest_len, manifest_sha256))
    {
        return 0;
    }
    if (memcmp(manifest_sha256, expected_manifest_sha256, sizeof(manifest_sha256)) != 0)
    {
        return 0;
    }
    memset(&verify_request, 0, sizeof(verify_request));
    verify_request.manifest_bytes = manifest_bytes;
    verify_request.manifest_len = manifest_len;
    memcpy(verify_request.manifest_sha256,
           manifest_sha256,
           sizeof(verify_request.manifest_sha256));
    verify_request.signature_der = signature_bytes;
    verify_request.signature_len = signature_len;
    verify_request.public_key_uncompressed = slot->public_key_uncompressed;
    verify_request.public_key_len = SC_PUBLIC_KEY_UNCOMPRESSED_LEN;
    return sc_ctrl_crypto_verify_ecdsa_p256_sha256_der(&verify_request);
}

static int sc_ctrl_parse_manifest_artifact_contract(const uint8_t *manifest_bytes,
                                                    uint32_t manifest_len,
                                                    ScManifestContract *out_contract)
{
    ScJsonSlice artifact_object;
    char sha256_hex[65];

    if ((manifest_bytes == NULL) || (manifest_len == 0U) || (out_contract == NULL))
    {
        return 0;
    }
    if (!sc_ctrl_json_find_object(manifest_bytes, manifest_len, "artifact", &artifact_object) ||
        !sc_ctrl_json_find_string_field(artifact_object.begin,
                                        artifact_object.len,
                                        "sha256",
                                        sha256_hex,
                                        sizeof(sha256_hex)) ||
        !sc_ctrl_parse_sha256_hex(sha256_hex, out_contract->artifact_sha256) ||
        !sc_ctrl_json_find_u32_field(artifact_object.begin,
                                     artifact_object.len,
                                     "size_bytes",
                                     &out_contract->artifact_size_bytes) ||
        !sc_ctrl_json_find_string_field(artifact_object.begin,
                                        artifact_object.len,
                                        "path",
                                        out_contract->artifact_path,
                                        sizeof(out_contract->artifact_path)) ||
        !sc_ctrl_json_find_string_field(artifact_object.begin,
                                        artifact_object.len,
                                        "format",
                                        out_contract->artifact_format,
                                        sizeof(out_contract->artifact_format)) ||
        !sc_ctrl_json_find_string_field(artifact_object.begin,
                                        artifact_object.len,
                                        "variant",
                                        out_contract->artifact_variant,
                                        sizeof(out_contract->artifact_variant)))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_parse_manifest_job_contract(const uint8_t *manifest_bytes,
                                               uint32_t manifest_len,
                                               ScManifestContract *out_contract)
{
    ScJsonSlice job_object;
    char job_flags_text[32];

    if ((manifest_bytes == NULL) || (manifest_len == 0U) || (out_contract == NULL))
    {
        return 0;
    }
    if (!sc_ctrl_json_find_object(manifest_bytes, manifest_len, "job", &job_object) ||
        !sc_ctrl_json_find_u32_field(job_object.begin,
                                     job_object.len,
                                     "deadline_ms",
                                     &out_contract->deadline_ms) ||
        !sc_ctrl_json_find_u32_field(job_object.begin,
                                     job_object.len,
                                     "expected_outputs",
                                     &out_contract->expected_outputs) ||
        !sc_ctrl_json_find_string_field(job_object.begin,
                                        job_object.len,
                                        "job_flags",
                                        job_flags_text,
                                        sizeof(job_flags_text)) ||
        !sc_ctrl_manifest_flag_from_string(job_flags_text, &out_contract->flags))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_parse_manifest_input_contract(const uint8_t *manifest_bytes,
                                                 uint32_t manifest_len,
                                                 ScManifestContract *out_contract)
{
    ScJsonSlice input_object;

    if ((manifest_bytes == NULL) || (manifest_len == 0U) || (out_contract == NULL))
    {
        return 0;
    }
    if (!sc_ctrl_json_find_object(manifest_bytes,
                                  manifest_len,
                                  "input_contract",
                                  &input_object) ||
        !sc_ctrl_json_find_u32_array4_field(input_object.begin,
                                            input_object.len,
                                            "shape",
                                            out_contract->input_shape) ||
        !sc_ctrl_json_find_string_field(input_object.begin,
                                        input_object.len,
                                        "dtype",
                                        out_contract->input_dtype,
                                        sizeof(out_contract->input_dtype)))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_parse_manifest_publisher_contract(const uint8_t *manifest_bytes,
                                                     uint32_t manifest_len,
                                                     ScManifestContract *out_contract)
{
    ScJsonSlice publisher_object;

    if ((manifest_bytes == NULL) || (manifest_len == 0U) || (out_contract == NULL))
    {
        return 0;
    }
    if (!sc_ctrl_json_find_object(manifest_bytes, manifest_len, "publisher", &publisher_object) ||
        !sc_ctrl_json_find_string_field(publisher_object.begin,
                                        publisher_object.len,
                                        "key_id",
                                        out_contract->publisher_key_id,
                                        sizeof(out_contract->publisher_key_id)) ||
        !sc_ctrl_json_find_string_field(publisher_object.begin,
                                        publisher_object.len,
                                        "channel",
                                        out_contract->publisher_channel,
                                        sizeof(out_contract->publisher_channel)))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_parse_manifest_provenance_contract(const uint8_t *manifest_bytes,
                                                      uint32_t manifest_len,
                                                      ScManifestContract *out_contract)
{
    ScJsonSlice provenance_object;

    if ((manifest_bytes == NULL) || (manifest_len == 0U) || (out_contract == NULL))
    {
        return 0;
    }
    if (!sc_ctrl_json_find_object(manifest_bytes,
                                  manifest_len,
                                  "provenance",
                                  &provenance_object) ||
        !sc_ctrl_json_find_string_field(provenance_object.begin,
                                        provenance_object.len,
                                        "created_at",
                                        out_contract->provenance_created_at,
                                        sizeof(out_contract->provenance_created_at)) ||
        !sc_ctrl_json_find_string_field(provenance_object.begin,
                                        provenance_object.len,
                                        "builder",
                                        out_contract->provenance_builder,
                                        sizeof(out_contract->provenance_builder)) ||
        !sc_ctrl_json_find_string_field(provenance_object.begin,
                                        provenance_object.len,
                                        "source_repo",
                                        out_contract->provenance_source_repo,
                                        sizeof(out_contract->provenance_source_repo)) ||
        !sc_ctrl_json_find_optional_string_field(provenance_object.begin,
                                                 provenance_object.len,
                                                 "source_git_commit",
                                                 out_contract->provenance_source_git_commit,
                                                 sizeof(out_contract->provenance_source_git_commit)) ||
        !sc_ctrl_json_find_optional_string_field(provenance_object.begin,
                                                 provenance_object.len,
                                                 "note",
                                                 out_contract->provenance_note,
                                                 sizeof(out_contract->provenance_note)))
    {
        return 0;
    }
    return 1;
}

static int sc_ctrl_parse_manifest_contract(const uint8_t *manifest_bytes,
                                           uint32_t manifest_len,
                                           ScManifestContract *out_contract)
{
    if ((manifest_bytes == NULL) || (manifest_len == 0U) || (out_contract == NULL))
    {
        return 0;
    }
    memset(out_contract, 0, sizeof(*out_contract));

    if (!sc_ctrl_json_expect_string_field(manifest_bytes,
                                          manifest_len,
                                          "schema",
                                          "openamp_artifact_manifest/v1",
                                          out_contract->schema_id,
                                          sizeof(out_contract->schema_id)))
    {
        return 0;
    }
    if (!sc_ctrl_json_expect_u32_field(manifest_bytes,
                                       manifest_len,
                                       "manifest_version",
                                       1U,
                                       &out_contract->manifest_version))
    {
        return 0;
    }
    if (!sc_ctrl_parse_manifest_artifact_contract(manifest_bytes,
                                                  manifest_len,
                                                  out_contract) ||
        !sc_ctrl_parse_manifest_job_contract(manifest_bytes,
                                             manifest_len,
                                             out_contract) ||
        !sc_ctrl_parse_manifest_input_contract(manifest_bytes,
                                               manifest_len,
                                               out_contract) ||
        !sc_ctrl_parse_manifest_publisher_contract(manifest_bytes,
                                                   manifest_len,
                                                   out_contract) ||
        !sc_ctrl_parse_manifest_provenance_contract(manifest_bytes,
                                                    manifest_len,
                                                    out_contract))
    {
        return 0;
    }
    return 1;
}

static uint32_t sc_ctrl_verify_signed_manifest_for_job_req(const ScCtrlHdr *request_header,
                                                           const ScJobReq *request)
{
    const ScPublicKeySlot *slot = NULL;
    ScManifestContract contract;

    if (!sc_ctrl_is_signed_stage_for_job(request_header->job_id) ||
        (sc_signed_stage.ready_for_job_req == 0U))
    {
        return SC_FAULT_MANIFEST_NOT_STAGED;
    }
    if (sc_signed_stage.job_id != request_header->job_id)
    {
        return SC_FAULT_MANIFEST_NOT_STAGED;
    }
    if (sc_ctrl_crc32(sc_signed_stage.manifest_buf, sc_signed_stage.manifest_len) !=
        sc_signed_stage.manifest_crc32)
    {
        return SC_FAULT_MANIFEST_DIGEST_MISMATCH;
    }
    if (!sc_ctrl_lookup_public_key_slot(sc_signed_stage.key_slot, &slot))
    {
        return SC_FAULT_KEY_SLOT_UNKNOWN;
    }
    if (!sc_ctrl_verify_manifest_signature(slot,
                                           sc_signed_stage.manifest_sha256,
                                           sc_signed_stage.manifest_buf,
                                           sc_signed_stage.manifest_len,
                                           sc_signed_stage.signature_buf,
                                           sc_signed_stage.signature_len))
    {
        return SC_FAULT_SIGNATURE_INVALID;
    }
    if (!sc_ctrl_parse_manifest_contract(sc_signed_stage.manifest_buf,
                                         sc_signed_stage.manifest_len,
                                         &contract))
    {
        return SC_FAULT_MANIFEST_PARSE_ERROR;
    }
    if ((strcmp(contract.publisher_key_id, slot->key_id) != 0) ||
        (strcmp(contract.publisher_channel, slot->channel) != 0) ||
        (memcmp(request->expected_sha256, contract.artifact_sha256,
                sizeof(contract.artifact_sha256)) != 0) ||
        (request->deadline_ms != contract.deadline_ms) ||
        (request->expected_outputs != contract.expected_outputs) ||
        (request->flags != contract.flags))
    {
        return SC_FAULT_MANIFEST_CONTRACT_MISMATCH;
    }
    return SC_FAULT_NONE;
}

static int sc_ctrl_send_job_ack(struct rpmsg_endpoint *ept, uint32_t src,
                                const ScCtrlHdr *request_header,
                                uint32_t decision, uint32_t fault_code)
{
    ScJobAckFrame response;

    memset(&response, 0, sizeof(response));
    ept->dest_addr = src;
    response.header.magic = SC_CTRL_MAGIC;
    response.header.version = SC_CTRL_VERSION;
    response.header.msg_type = SC_MSG_JOB_ACK;
    response.header.seq = request_header->seq;
    response.header.job_id = request_header->job_id;
    response.header.payload_len = sizeof(response.payload);
    response.header.header_crc32 = sc_ctrl_compute_header_crc(&response.header);
    response.payload.decision = decision;
    response.payload.fault_code = fault_code;
    response.payload.guard_state = sc_guard_state;

    return rpmsg_send(ept, &response, sizeof(response));
}

static int sc_ctrl_send_heartbeat_ack(struct rpmsg_endpoint *ept, uint32_t src,
                                      const ScCtrlHdr *request_header,
                                      uint32_t heartbeat_ok)
{
    ScHeartbeatAckFrame response;

    memset(&response, 0, sizeof(response));
    ept->dest_addr = src;
    response.header.magic = SC_CTRL_MAGIC;
    response.header.version = SC_CTRL_VERSION;
    response.header.msg_type = SC_MSG_HEARTBEAT_ACK;
    response.header.seq = request_header->seq;
    response.header.job_id = request_header->job_id;
    response.header.payload_len = sizeof(response.payload);
    response.header.header_crc32 = sc_ctrl_compute_header_crc(&response.header);
    response.payload.guard_state = sc_guard_state;
    response.payload.heartbeat_ok = heartbeat_ok;

    return rpmsg_send(ept, &response, sizeof(response));
}

static int sc_ctrl_send_status_resp(struct rpmsg_endpoint *ept, uint32_t src,
                                    const ScCtrlHdr *request_header)
{
    ScStatusRespFrame response;

    sc_ctrl_normalize_runtime_state();
    memset(&response, 0, sizeof(response));
    ept->dest_addr = src;
    response.header.magic = SC_CTRL_MAGIC;
    response.header.version = SC_CTRL_VERSION;
    response.header.msg_type = SC_MSG_STATUS_RESP;
    response.header.seq = request_header->seq;
    response.header.job_id = request_header->job_id;
    response.header.payload_len = sizeof(response.payload);
    response.header.header_crc32 = sc_ctrl_compute_header_crc(&response.header);
    response.payload.guard_state = sc_guard_state;
    response.payload.active_job_id = sc_active_job_id;
    response.payload.last_fault_code = sc_last_fault_code;
    response.payload.heartbeat_ok = (sc_ctrl_has_admitted_job() &&
                                     (sc_heartbeat_seen != 0U)) ? 1U : 0U;
    response.payload.sticky_fault = 0U;
    response.payload.total_fault_count = sc_total_fault_count;

    return rpmsg_send(ept, &response, sizeof(response));
}

static int sc_ctrl_send_mode_directive(struct rpmsg_endpoint *ept, uint32_t src,
                                       const ScCtrlHdr *request_header,
                                       uint32_t reason_code)
{
    ScModeDirectiveFrame response;

    memset(&response, 0, sizeof(response));
    ept->dest_addr = src;
    response.header.magic = SC_CTRL_MAGIC;
    response.header.version = SC_CTRL_VERSION;
    response.header.msg_type = SC_MSG_MODE_DIRECTIVE;
    response.header.seq = request_header->seq;
    response.header.job_id = request_header->job_id;
    response.header.payload_len = sizeof(response.payload);
    response.header.header_crc32 = sc_ctrl_compute_header_crc(&response.header);
    response.payload.applied_mode = sc_current_mode;
    response.payload.allowed_mode = sc_allowed_mode;
    response.payload.reason_code = reason_code;
    response.payload.mode_transitions = sc_mode_transition_count;

    return rpmsg_send(ept, &response, sizeof(response));
}

static uint32_t sc_ctrl_compute_target_service_mode(const ScLinkHealth *report)
{
    if (report->per_x1000 > SC_MODE_PER_ALERT_THRESHOLD)
    {
        return SC_SERVICE_MODE_ALERT_ONLY;
    }
    if ((report->per_x1000 > SC_MODE_PER_ROI_THRESHOLD) ||
        (report->snr_est_db_x100 < SC_MODE_SNR_ROI_THRESHOLD))
    {
        return SC_SERVICE_MODE_ROI_ONLY;
    }
    return SC_SERVICE_MODE_FULL_FRAME;
}

static void sc_ctrl_commit_service_mode(uint32_t mode, uint32_t reason_code)
{
    if (sc_current_mode != mode)
    {
        sc_mode_transition_count += 1U;
    }
    sc_current_mode = mode;
    sc_allowed_mode = mode;
    sc_last_mode_reason = reason_code;
}

static int sc_ctrl_handle_job_req(struct rpmsg_endpoint *ept, uint32_t src,
                                  const ScCtrlHdr *request_header,
                                  const void *payload_data)
{
    ScJobReq request;
    int signed_path_requested = 0;
    uint8_t signed_key_slot = 0U;
    uint32_t signed_manifest_len = 0U;
    uint32_t fault_code = SC_FAULT_NONE;
    int ret;

    sc_ctrl_normalize_runtime_state();
    if (request_header->payload_len != sizeof(request))
    {
        fault_code = SC_FAULT_PARAM_RANGE;
        goto deny_request;
    }

    memcpy(&request, payload_data, sizeof(request));

    if ((sc_guard_state != SC_GUARD_STATE_READY) || (sc_active_job_id != 0U))
    {
        fault_code = SC_FAULT_DUPLICATE_JOB;
        goto deny_request;
    }

    signed_path_requested = sc_ctrl_is_signed_stage_for_job(request_header->job_id);
    if (signed_path_requested)
    {
        fault_code = sc_ctrl_verify_signed_manifest_for_job_req(request_header, &request);
        if (fault_code != SC_FAULT_NONE)
        {
            goto deny_request;
        }
        signed_key_slot = sc_signed_stage.key_slot;
        signed_manifest_len = sc_signed_stage.manifest_len;
        sc_ctrl_clear_signed_stage();
    }
    else if (memcmp(request.expected_sha256, sc_trusted_sha256,
                    sizeof(sc_trusted_sha256)) != 0)
    {
        fault_code = SC_FAULT_ARTIFACT_SHA;
        goto deny_request;
    }

    if (request.deadline_ms == 0U)
    {
        fault_code = SC_FAULT_PARAM_RANGE;
        goto deny_request;
    }

    if ((request.expected_outputs != 1U) && (request.expected_outputs != 300U))
    {
        fault_code = SC_FAULT_PARAM_RANGE;
        goto deny_request;
    }

    if (!sc_ctrl_is_known_flag(request.flags))
    {
        fault_code = SC_FAULT_PARAM_RANGE;
        goto deny_request;
    }

    sc_last_fault_code = SC_FAULT_NONE;
    sc_active_job_id = request_header->job_id;
    sc_guard_state = SC_GUARD_STATE_JOB_ACTIVE;
    sc_heartbeat_seen = 0U;
    sc_expected_outputs = request.expected_outputs;

    ret = sc_ctrl_send_job_ack(ept, src, request_header, SC_DECISION_ALLOW,
                               SC_FAULT_NONE);
    if (ret < 0)
    {
        return ret;
    }

    if (signed_path_requested)
    {
        SLAVE_DEBUG_I("JOB_REQ signed allow seq:%u job_id:%u slot:%u manifest_len:%u outputs:%u flags:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)signed_key_slot,
                      (unsigned int)signed_manifest_len,
                      (unsigned int)request.expected_outputs,
                      (unsigned int)request.flags);
    }
    else
    {
        SLAVE_DEBUG_I("JOB_REQ allow seq:%u job_id:%u outputs:%u flags:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)request.expected_outputs,
                      (unsigned int)request.flags);
    }
    return RPMSG_SUCCESS;

deny_request:
    if (signed_path_requested && (fault_code >= SC_FAULT_MANIFEST_NOT_STAGED))
    {
        sc_ctrl_clear_signed_stage();
    }
    sc_ctrl_note_fault(fault_code);
    sc_ctrl_normalize_runtime_state();

    ret = sc_ctrl_send_job_ack(ept, src, request_header, SC_DECISION_DENY,
                               fault_code);
    if (ret < 0)
    {
        return ret;
    }

    SLAVE_DEBUG_W("JOB_REQ deny seq:%u job_id:%u fault:%u guard:%u active:%u",
                  (unsigned int)request_header->seq,
                  (unsigned int)request_header->job_id,
                  (unsigned int)fault_code,
                  (unsigned int)sc_guard_state,
                  (unsigned int)sc_active_job_id);
    return RPMSG_SUCCESS;
}

static int sc_ctrl_handle_heartbeat(struct rpmsg_endpoint *ept, uint32_t src,
                                    const ScCtrlHdr *request_header,
                                    const void *payload_data)
{
    ScHeartbeat request;
    uint32_t heartbeat_ok = 0U;
    int ret;

    sc_ctrl_normalize_runtime_state();
    if (request_header->payload_len != sizeof(request))
    {
        ret = sc_ctrl_send_heartbeat_ack(ept, src, request_header, 0U);
        if (ret < 0)
        {
            return ret;
        }

        SLAVE_DEBUG_W("HEARTBEAT invalid payload_len:%u seq:%u job_id:%u",
                      (unsigned int)request_header->payload_len,
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id);
        return RPMSG_SUCCESS;
    }

    memcpy(&request, payload_data, sizeof(request));

    if (sc_ctrl_has_admitted_job() &&
        (request_header->job_id == sc_active_job_id))
    {
        sc_heartbeat_seen = 1U;
        heartbeat_ok = 1U;
    }

    ret = sc_ctrl_send_heartbeat_ack(ept, src, request_header, heartbeat_ok);
    if (ret < 0)
    {
        return ret;
    }

    if (heartbeat_ok != 0U)
    {
        SLAVE_DEBUG_I("HEARTBEAT ack seq:%u job_id:%u elapsed:%u progress:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)request.elapsed_ms,
                      (unsigned int)request.progress_x100);
    }
    else
    {
        SLAVE_DEBUG_W("HEARTBEAT ignore seq:%u job_id:%u guard:%u active:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)sc_guard_state,
                      (unsigned int)sc_active_job_id);
    }

    return RPMSG_SUCCESS;
}

static int sc_ctrl_handle_link_health(struct rpmsg_endpoint *ept, uint32_t src,
                                      const ScCtrlHdr *request_header,
                                      const void *payload_data)
{
    ScLinkHealth request;
    uint32_t target_mode = sc_current_mode;
    uint32_t reason_code = SC_MODE_REASON_NONE;
    int ret;

    sc_ctrl_normalize_runtime_state();
    if (request_header->payload_len != sizeof(request))
    {
        ret = sc_ctrl_send_mode_directive(ept, src, request_header, reason_code);
        if (ret < 0)
        {
            return ret;
        }

        SLAVE_DEBUG_W("LINK_HEALTH invalid payload_len:%u seq:%u job_id:%u",
                      (unsigned int)request_header->payload_len,
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id);
        return RPMSG_SUCCESS;
    }

    memcpy(&request, payload_data, sizeof(request));

    if (sc_ctrl_has_admitted_job() &&
        (request_header->job_id == sc_active_job_id))
    {
        if (request.rx_locked == 0U)
        {
            sc_ctrl_note_fault(SC_FAULT_LINK_LOST);
            sc_ctrl_clear_active_job();
            sc_ctrl_clear_signed_stage();
            ret = sc_ctrl_send_status_resp(ept, src, request_header);
            if (ret < 0)
            {
                return ret;
            }

            SLAVE_DEBUG_W("LINK_HEALTH safe_stop seq:%u job_id:%u guard:%u fault:%u",
                          (unsigned int)request_header->seq,
                          (unsigned int)request_header->job_id,
                          (unsigned int)sc_guard_state,
                          (unsigned int)sc_last_fault_code);
            return RPMSG_SUCCESS;
        }
        else if (request.burst_loss_max >= SC_MODE_BURST_LOSS_EMERGENCY)
        {
            sc_ctrl_commit_service_mode(SC_SERVICE_MODE_ALERT_ONLY,
                                        SC_MODE_REASON_BURST_LOSS_EMERGENCY);
            sc_mode_degrade_window_count = 0U;
            sc_mode_upgrade_window_count = 0U;
            reason_code = SC_MODE_REASON_BURST_LOSS_EMERGENCY;
        }
        else
        {
            target_mode = sc_ctrl_compute_target_service_mode(&request);
            if (target_mode > sc_current_mode)
            {
                sc_mode_degrade_window_count += 1U;
                sc_mode_upgrade_window_count = 0U;
                if (sc_mode_degrade_window_count >= SC_MODE_DEGRADE_THRESHOLD)
                {
                    sc_ctrl_commit_service_mode(target_mode,
                                                SC_MODE_REASON_SUSTAINED_DEGRADATION);
                    sc_mode_degrade_window_count = 0U;
                    reason_code = SC_MODE_REASON_SUSTAINED_DEGRADATION;
                }
            }
            else if (target_mode < sc_current_mode)
            {
                sc_mode_upgrade_window_count += 1U;
                sc_mode_degrade_window_count = 0U;
                if (sc_mode_upgrade_window_count >= SC_MODE_UPGRADE_THRESHOLD)
                {
                    sc_ctrl_commit_service_mode(target_mode,
                                                SC_MODE_REASON_SUSTAINED_RECOVERY);
                    sc_mode_upgrade_window_count = 0U;
                    reason_code = SC_MODE_REASON_SUSTAINED_RECOVERY;
                }
            }
            else
            {
                sc_mode_degrade_window_count = 0U;
                sc_mode_upgrade_window_count = 0U;
            }
        }
    }
    else
    {
        SLAVE_DEBUG_W("LINK_HEALTH ignore seq:%u job_id:%u guard:%u active:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)sc_guard_state,
                      (unsigned int)sc_active_job_id);
    }

    ret = sc_ctrl_send_mode_directive(ept, src, request_header, reason_code);
    if (ret < 0)
    {
        return ret;
    }

    SLAVE_DEBUG_I("LINK_HEALTH ack seq:%u job_id:%u mode:%u reason:%u transitions:%u",
                  (unsigned int)request_header->seq,
                  (unsigned int)request_header->job_id,
                  (unsigned int)sc_current_mode,
                  (unsigned int)reason_code,
                  (unsigned int)sc_mode_transition_count);
    return RPMSG_SUCCESS;
}

static int sc_ctrl_handle_mode_ack(struct rpmsg_endpoint *ept, uint32_t src,
                                   const ScCtrlHdr *request_header,
                                   const void *payload_data)
{
    ScModeAck request;

    (void)ept;
    (void)src;

    if (request_header->payload_len != sizeof(request))
    {
        SLAVE_DEBUG_W("MODE_ACK invalid payload_len:%u seq:%u job_id:%u",
                      (unsigned int)request_header->payload_len,
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id);
        return RPMSG_SUCCESS;
    }

    memcpy(&request, payload_data, sizeof(request));
    if (request.applied_mode != sc_current_mode)
    {
        SLAVE_DEBUG_W("MODE_ACK stale seq:%u job_id:%u applied:%u current:%u status:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)request.applied_mode,
                      (unsigned int)sc_current_mode,
                      (unsigned int)request.ack_status);
    }
    else
    {
        SLAVE_DEBUG_I("MODE_ACK ok seq:%u job_id:%u applied:%u status:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)request.applied_mode,
                      (unsigned int)request.ack_status);
    }
    return RPMSG_SUCCESS;
}

static int sc_ctrl_handle_job_done(struct rpmsg_endpoint *ept, uint32_t src,
                                   const ScCtrlHdr *request_header,
                                   const void *payload_data)
{
    ScJobDone request;
    int done_applied = 0;
    uint32_t expected_outputs = 0U;
    int ret;

    sc_ctrl_normalize_runtime_state();
    if ((request_header->payload_len == sizeof(request)) &&
        sc_ctrl_has_admitted_job() &&
        (request_header->job_id == sc_active_job_id))
    {
        memcpy(&request, payload_data, sizeof(request));
        expected_outputs = sc_expected_outputs;
        if (request.result_code == 0U)
        {
            sc_last_fault_code = SC_FAULT_NONE;
            sc_ctrl_clear_active_job();
            sc_ctrl_clear_signed_stage();
        }
        else
        {
            sc_ctrl_note_fault(SC_FAULT_OUTPUT_INCOMPLETE);
            sc_ctrl_clear_active_job();
            sc_ctrl_clear_signed_stage();
        }
        done_applied = 1;
    }

    ret = sc_ctrl_send_status_resp(ept, src, request_header);
    if (ret < 0)
    {
        return ret;
    }

    if (done_applied != 0)
    {
        SLAVE_DEBUG_I("JOB_DONE applied seq:%u job_id:%u result:%u outputs:%u expected:%u fault:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)request.result_code,
                      (unsigned int)request.output_count,
                      (unsigned int)expected_outputs,
                      (unsigned int)sc_last_fault_code);
    }
    else if (request_header->payload_len != sizeof(request))
    {
        SLAVE_DEBUG_W("JOB_DONE invalid payload_len:%u seq:%u job_id:%u",
                      (unsigned int)request_header->payload_len,
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id);
    }
    else
    {
        SLAVE_DEBUG_W("JOB_DONE ignore seq:%u job_id:%u guard:%u active:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)sc_guard_state,
                      (unsigned int)sc_active_job_id);
    }

    return RPMSG_SUCCESS;
}

static int sc_ctrl_handle_safe_stop(struct rpmsg_endpoint *ept, uint32_t src,
                                    const ScCtrlHdr *request_header)
{
    int stop_applied = 0;
    int ret;

    sc_ctrl_normalize_runtime_state();
    if ((request_header->payload_len == 0U) &&
        sc_ctrl_has_admitted_job() &&
        (request_header->job_id == sc_active_job_id))
    {
        sc_ctrl_note_fault(SC_FAULT_MANUAL_SAFE_STOP);
        sc_ctrl_clear_active_job();
        sc_ctrl_clear_signed_stage();
        stop_applied = 1;
    }

    ret = sc_ctrl_send_status_resp(ept, src, request_header);
    if (ret < 0)
    {
        return ret;
    }

    if (stop_applied != 0)
    {
        SLAVE_DEBUG_W("SAFE_STOP applied seq:%u job_id:%u fault:%u total_faults:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)sc_last_fault_code,
                      (unsigned int)sc_total_fault_count);
    }
    else if (request_header->payload_len != 0U)
    {
        SLAVE_DEBUG_W("SAFE_STOP invalid payload_len:%u seq:%u job_id:%u",
                      (unsigned int)request_header->payload_len,
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id);
    }
    else
    {
        SLAVE_DEBUG_W("SAFE_STOP ignore seq:%u job_id:%u guard:%u active:%u",
                      (unsigned int)request_header->seq,
                      (unsigned int)request_header->job_id,
                      (unsigned int)sc_guard_state,
                      (unsigned int)sc_active_job_id);
    }

    return RPMSG_SUCCESS;
}

/*-----------------------------------------------------------------------------*
 *  RPMSG endpoint callbacks
 *-----------------------------------------------------------------------------*/
static int rpmsg_endpoint_cb(struct rpmsg_endpoint *ept, void *data, size_t len, uint32_t src, void *priv)
{
    ScCtrlHdr header = {0};
    const uint8_t *payload_data = NULL;
    unsigned int shutdown_msg = 0U;
    int ret;

    (void)priv;
    /* On reception of a shutdown we signal the application to terminate */
    if (len >= sizeof(shutdown_msg))
    {
        memcpy(&shutdown_msg, data, sizeof(shutdown_msg));
        if (shutdown_msg == SHUTDOWN_MSG)
        {
            SLAVE_DEBUG_I("Shutdown message is received.\r\n");
            shutdown_req = 1;
            return RPMSG_SUCCESS;
        }
    }

    ret = sc_ctrl_parse_header(data, len, &header);
    if (ret != 0)
    {
        SLAVE_DEBUG_W("ignore non control frame, len:%lu, ret:%d",
                      (unsigned long)len, ret);
        return RPMSG_SUCCESS;
    }

    payload_data = ((const uint8_t *)data) + sizeof(ScCtrlHdr);

    switch (header.msg_type)
    {
        case SC_MSG_STATUS_REQ:
            if (header.payload_len != 0U)
            {
                SLAVE_DEBUG_W("ignore STATUS_REQ with payload_len:%u",
                              (unsigned int)header.payload_len);
                return RPMSG_SUCCESS;
            }

            ret = sc_ctrl_send_status_resp(ept, src, &header);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send status resp failed.\r\n");
                return ret;
            }

            SLAVE_DEBUG_I("STATUS_REQ seq:%u job_id:%u -> STATUS_RESP guard:%u active:%u",
                          (unsigned int)header.seq,
                          (unsigned int)header.job_id,
                          (unsigned int)sc_guard_state,
                          (unsigned int)sc_active_job_id);
            return RPMSG_SUCCESS;

        case SC_MSG_SIGNED_ADMISSION_BEGIN:
            ret = sc_ctrl_handle_signed_admission_begin(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send signed begin ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_SIGNED_ADMISSION_CHUNK:
            ret = sc_ctrl_handle_signed_admission_chunk(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send signed chunk ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_SIGNED_ADMISSION_SIGNATURE:
            ret = sc_ctrl_handle_signed_admission_signature(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send signed signature ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_SIGNED_ADMISSION_COMMIT:
            ret = sc_ctrl_handle_signed_admission_commit(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send signed commit ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_JOB_REQ:
            ret = sc_ctrl_handle_job_req(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send job ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_HEARTBEAT:
            ret = sc_ctrl_handle_heartbeat(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send heartbeat ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_LINK_HEALTH:
            ret = sc_ctrl_handle_link_health(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send mode directive failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_MODE_ACK:
            ret = sc_ctrl_handle_mode_ack(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("handle mode ack failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_JOB_DONE:
            ret = sc_ctrl_handle_job_done(ept, src, &header, payload_data);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send job done status failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        case SC_MSG_SAFE_STOP:
            ret = sc_ctrl_handle_safe_stop(ept, src, &header);
            if (ret < 0)
            {
                SLAVE_DEBUG_E("rpmsg_send safe stop status failed.\r\n");
                return ret;
            }
            return RPMSG_SUCCESS;

        default:
            SLAVE_DEBUG_W("ignore unsupported msg_type:0x%x, seq:%u, job_id:%u",
                          (unsigned int)header.msg_type,
                          (unsigned int)header.seq,
                          (unsigned int)header.job_id);
            return RPMSG_SUCCESS;
    }
}

static void rpmsg_service_unbind(struct rpmsg_endpoint *ept)
{
    (void)ept;
    SLAVE_DEBUG_I("Unexpected remote endpoint destroy.\r\n");
    shutdown_req = 1;
}

/*-----------------------------------------------------------------------------*
 *  Application
 *-----------------------------------------------------------------------------*/
static int FRpmsgEchoApp(struct rpmsg_device *rdev, void *priv)
{
    int ret = 0;
    struct rpmsg_endpoint lept;
    shutdown_req = 0;
    /* Initialize RPMSG framework */
    SLAVE_DEBUG_I("Try to create rpmsg endpoint.\r\n");

    ret = rpmsg_create_ept(&lept, rdev, RPMSG_SERVICE_NAME, 0, RPMSG_ADDR_ANY, rpmsg_endpoint_cb, rpmsg_service_unbind);
    if (ret)
    {
        SLAVE_DEBUG_E("Failed to create endpoint. %d \r\n", ret);
        return -1;
    }

    SLAVE_DEBUG_I("Successfully created rpmsg endpoint.\r\n");

    while (1)
    {
        platform_poll(priv);
        /* we got a shutdown request, exit */
        if (shutdown_req)
        {
            break;
        }
    }

    rpmsg_destroy_ept(&lept);

    return ret;
}

/*-----------------------------------------------------------------------------*
 *  Application entry point
 *-----------------------------------------------------------------------------*/
int slave_init(void)
{
    init_system();  // Initialize the system resources and environment
    
    if (!platform_create_proc(&remoteproc_slave_00, &slave_00_priv, &kick_driver_00)) 
    {
        SLAVE_DEBUG_E("Failed to create remoteproc instance for slave 00\r\n");
        return -1;  // Return with an error if creation fails
    }
    
    remoteproc_slave_00.rsc_table = &resources;

    if (platform_setup_src_table(&remoteproc_slave_00,remoteproc_slave_00.rsc_table)) 
    {
        SLAVE_DEBUG_E("Failed to setup src table for slave 00\r\n");
        return -1;  // Return with an error if setup fails
    }
    
    SLAVE_DEBUG_I("Setup resource tables for the created remoteproc instances is over \r\n");

    if (platform_setup_share_mems(&remoteproc_slave_00)) 
    {
        SLAVE_DEBUG_E("Failed to setup shared memory for slave 00\r\n");
        return -1;  // Return with an error if setup fails
    }

    SLAVE_DEBUG_I("Setup shared memory regions for both remoteproc instances is over \r\n");

    rpdev_slave_00 = platform_create_rpmsg_vdev(&remoteproc_slave_00, 0, VIRTIO_DEV_SLAVE, NULL, NULL);
    if (!rpdev_slave_00) 
    {
        SLAVE_DEBUG_E("Failed to create rpmsg vdev for slave 00\r\n");
        return -1;  // Return with an error if creation fails
    }

    return 0 ;   
}

int slave00_rpmsg_echo_process(void)
{
    int ret = 0;
    SLAVE_DEBUG_I("Starting application...");
    if(!slave_init())
    {
        sc_ctrl_reset_runtime_state();
        ret = FRpmsgEchoApp(rpdev_slave_00,&remoteproc_slave_00) ;
        if (ret)
        {
            SLAVE_DEBUG_E("Failed to running echoapp");
            return platform_cleanup(&remoteproc_slave_00);
        }
        platform_release_rpmsg_vdev(rpdev_slave_00, &remoteproc_slave_00);
        SLAVE_DEBUG_I("Stopping application...");
        platform_cleanup(&remoteproc_slave_00);
        return ret;
    }
    else
    {
        platform_cleanup(&remoteproc_slave_00);
        SLAVE_DEBUG_E("Failed to init remoteproc.\r\n");
    }
    return 0 ;
}
