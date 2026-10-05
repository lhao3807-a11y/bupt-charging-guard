import { describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useConfigEditor } from './useConfigEditor'
import type { SystemConfig } from '@/types/contract'

const rows = (): SystemConfig[] => [
  { key: 'full_timeout_min', value: '30', note: '充满超时阈值' },
  { key: 'abnormal_park_min', value: '40', note: '异常占位久停阈值' },
]
const connect = (
  read = vi.fn().mockResolvedValue(rows()),
  write = vi.fn().mockResolvedValue(undefined),
) => ({ editor: useConfigEditor({ loadConfig: read, saveConfig: write }), read, write })
describe('system configuration editor', () => {
  it('does not invent threshold defaults or allow saving without a data source', async () => {
    const editor = useConfigEditor()
    await editor.reload()
    expect(editor.data.value).toBeNull()
    expect(editor.drafts.full_timeout_min).toBeUndefined()
    expect(editor.canSave.value).toBe(false)
    expect(editor.prepareSave()).toBe(false)
  })
  it('edits only existing known rows, leaving unknown keys readonly and missing keys absent', async () => {
    const { editor, write } = connect(
      vi.fn().mockResolvedValue([
        { key: 'full_timeout_min', value: '30', note: '' },
        { key: 'other', value: '10', note: '' },
      ]),
    )
    await editor.reload()
    editor.drafts.abnormal_park_min = 50
    editor.drafts.full_timeout_min = 45
    expect(editor.changes.value).toEqual([{ key: 'full_timeout_min', before: '30', after: 45 }])
    editor.prepareSave()
    await editor.confirmSave()
    expect(write).toHaveBeenCalledWith([{ key: 'full_timeout_min', before: '30', after: 45 }])
  })
  it.each([0, -1, 1.5, undefined, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1])(
    'rejects invalid threshold %s before confirmation',
    async (value: number | undefined) => {
      const { editor, write } = connect()
      await editor.reload()
      editor.drafts.full_timeout_min = value
      expect(editor.validation.value.full_timeout_min).toBeTruthy()
      expect(editor.prepareSave()).toBe(false)
      expect(write).not.toHaveBeenCalled()
    },
  )
  it('does not replace invalid server values with a fallback, but allows an explicit correction', async () => {
    const { editor } = connect(
      vi.fn().mockResolvedValue([{ key: 'full_timeout_min', value: 'broken', note: '' }]),
    )
    await editor.reload()
    expect(editor.drafts.full_timeout_min).toBeUndefined()
    editor.drafts.full_timeout_min = 45
    expect(editor.changes.value).toEqual([{ key: 'full_timeout_min', before: 'broken', after: 45 }])
    expect(editor.canSave.value).toBe(true)
  })
  it('cancelling confirmation preserves drafts and makes no write', async () => {
    const { editor, write } = connect()
    await editor.reload()
    editor.drafts.full_timeout_min = 45
    expect(editor.prepareSave()).toBe(true)
    expect(editor.confirmationText.value).toContain('30 → 45')
    editor.cancelSave()
    expect(editor.dirty.value).toBe(true)
    expect(editor.confirming.value).toBe(false)
    expect(write).not.toHaveBeenCalled()
  })
  it('saves the confirmed snapshot only once while a write is pending', async () => {
    let done!: () => void
    const { editor, write } = connect(
      vi.fn().mockResolvedValue(rows()),
      vi.fn(
        () =>
          new Promise<void>((resolve) => {
            done = resolve
          }),
      ),
    )
    await editor.reload()
    editor.drafts.full_timeout_min = 45
    editor.prepareSave()
    editor.drafts.full_timeout_min = 60
    const saving = editor.confirmSave()
    await editor.confirmSave()
    expect(write).toHaveBeenCalledTimes(1)
    expect(write).toHaveBeenCalledWith([{ key: 'full_timeout_min', before: '30', after: 45 }])
    done()
    await saving
  })
  it('keeps draft values after a failed save', async () => {
    const { editor } = connect(
      vi.fn().mockResolvedValue(rows()),
      vi.fn().mockRejectedValue(new Error('offline')),
    )
    await editor.reload()
    editor.drafts.abnormal_park_min = 55
    editor.prepareSave()
    expect(await editor.confirmSave()).toBe(false)
    expect(editor.drafts.abnormal_park_min).toBe(55)
    expect(editor.dirty.value).toBe(true)
    expect(editor.notice.value?.tone).toBe('error')
    expect(editor.saving.value).toBe(false)
  })
  it('rereads saved values and only then clears the dirty state', async () => {
    const updated = rows()
    updated[0]!.value = '45'
    const { editor, read } = connect(
      vi.fn().mockResolvedValueOnce(rows()).mockResolvedValueOnce(updated),
    )
    await editor.reload()
    editor.drafts.full_timeout_min = 45
    editor.prepareSave()
    expect(await editor.confirmSave()).toBe(true)
    expect(read).toHaveBeenCalledTimes(2)
    expect(editor.drafts.full_timeout_min).toBe(45)
    expect(editor.dirty.value).toBe(false)
    expect(editor.notice.value?.tone).toBe('success')
  })
  it('separates completed save from failed reread and prevents another write until reload', async () => {
    const { editor, write } = connect(
      vi.fn().mockResolvedValueOnce(rows()).mockRejectedValueOnce(new Error('offline')),
    )
    await editor.reload()
    editor.drafts.full_timeout_min = 45
    editor.prepareSave()
    await editor.confirmSave()
    expect(write).toHaveBeenCalledTimes(1)
    expect(editor.notice.value?.tone).toBe('warning')
    expect(editor.data.value).toBeNull()
    expect(editor.canSave.value).toBe(false)
  })
  it('requires undo before refreshing dirty values', async () => {
    const { editor, read } = connect()
    await editor.reload()
    editor.drafts.full_timeout_min = 45
    expect(await editor.reload()).toBe(false)
    expect(read).toHaveBeenCalledTimes(1)
    editor.undo()
    expect(editor.drafts.full_timeout_min).toBe(30)
    expect(editor.dirty.value).toBe(false)
    await editor.reload()
    expect(read).toHaveBeenCalledTimes(2)
  })
  it('does not reread or show success after leaving the page during a save', async () => {
    let done!: () => void
    const scope = effectScope()
    const read = vi.fn().mockResolvedValue(rows())
    const editor = scope.run(() =>
      useConfigEditor({
        loadConfig: read,
        saveConfig: () =>
          new Promise<void>((resolve) => {
            done = resolve
          }),
      }),
    )!
    await editor.reload()
    editor.drafts.full_timeout_min = 45
    editor.prepareSave()
    const saving = editor.confirmSave()
    scope.stop()
    done()
    await saving
    expect(read).toHaveBeenCalledTimes(1)
    expect(editor.notice.value).toBeNull()
  })
})
