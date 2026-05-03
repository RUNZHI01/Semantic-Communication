import test from 'node:test'
import assert from 'node:assert/strict'

import { comparisonResultFromInferencePayload } from './comparisonResult.js'

test('baseline reference result can hydrate comparison from runner summary fallback', () => {
  const result = comparisonResultFromInferencePayload({
    status: 'success',
    execution_mode: 'reference',
    variant: 'baseline',
    runner_summary: {
      processed_count: 300,
      total_wall_ms: 105000,
    },
  })

  assert.deepEqual(result, {
    engine: 'pytorch',
    label: 'PyTorch参考',
    reconstructionMs: 350,
    runMs: 350,
    sampleCount: 300,
    quality: undefined,
  })
})

test('current live result falls back to nested pipeline summary when timings are absent', () => {
  const result = comparisonResultFromInferencePayload({
    status: 'success',
    execution_mode: 'live',
    variant: 'current',
    runner_summary: {
      pipeline: {
        processed_count: 300,
        ms_per_image: 251.4,
        run_median_ms: 239.8,
      },
    },
  })

  assert.deepEqual(result, {
    engine: 'tvm',
    label: 'TVM重建',
    reconstructionMs: 251.4,
    runMs: 239.8,
    sampleCount: 300,
    quality: undefined,
  })
})

test('current live result preserves quality metrics for display', () => {
  const result = comparisonResultFromInferencePayload({
    status: 'success',
    execution_mode: 'live',
    variant: 'current',
    timings: {
      total_ms: 251.4,
      payload_ms: 239.8,
    },
    quality: {
      psnr_db: 37.0445,
      ssim: 0.9749,
    },
  })

  assert.deepEqual(result, {
    engine: 'tvm',
    label: 'TVM重建',
    reconstructionMs: 251.4,
    runMs: 239.8,
    sampleCount: undefined,
    quality: {
      psnr_db: 37.0445,
      ssim: 0.9749,
    },
  })
})

test('current prerecorded result is ignored for comparison', () => {
  const result = comparisonResultFromInferencePayload({
    status: 'success',
    execution_mode: 'prerecorded',
    variant: 'current',
    timings: {
      total_ms: 123.4,
    },
  })

  assert.equal(result, undefined)
})

test('baseline fallback reference result still hydrates comparison from timings', () => {
  const result = comparisonResultFromInferencePayload({
    status: 'fallback',
    execution_mode: 'reference',
    variant: 'baseline',
    timings: {
      total_ms: 412.8,
      payload_ms: 412.8,
    },
  })

  assert.deepEqual(result, {
    engine: 'pytorch',
    label: 'PyTorch参考',
    reconstructionMs: 412.8,
    runMs: 412.8,
    sampleCount: undefined,
    quality: undefined,
  })
})
