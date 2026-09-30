import { addDays, format, isSameDay, isSameMonth, isSameYear, startOfDay } from 'date-fns'

import type { ViewMode } from '@/lib/calendar'
import type { Meeting } from '@/lib/api'

export function formatWhen(meeting: Meeting): string {
  const start = new Date(meeting.starts_at)
  const end = new Date(meeting.ends_at)
  const day = format(start, 'EEE, d MMM yyyy')
  if (isSameDay(start, end)) {
    return `${day} · ${format(start, 'HH:mm')}–${format(end, 'HH:mm')}`
  }
  return `${day} ${format(start, 'HH:mm')} – ${format(end, 'EEE, d MMM HH:mm')}`
}

/** The part of a meeting that falls on `day`, e.g. `10:00–11:00`, `from 18:00`, `until 09:00`. */
export function formatTimeOnDay(meeting: Meeting, day: Date): string {
  const start = new Date(meeting.starts_at)
  const end = new Date(meeting.ends_at)
  const startsToday = isSameDay(start, day)
  const endsToday = end <= addDays(startOfDay(day), 1)
  if (startsToday && endsToday) return `${format(start, 'HH:mm')}–${format(end, 'HH:mm')}`
  if (startsToday) return `from ${format(start, 'HH:mm')}`
  if (endsToday) return `until ${format(end, 'HH:mm')}`
  return 'All day'
}

/** Heading for the visible range: `Monday, 28 September 2026` or `25 Sep – 1 Oct 2026`. */
export function formatRange(mode: ViewMode, days: Date[]): string {
  const first = days[0]
  const last = days[days.length - 1]
  if (mode === 'day') return format(first, 'EEEE, d MMMM yyyy')
  if (isSameMonth(first, last)) return `${format(first, 'd')}–${format(last, 'd MMMM yyyy')}`
  if (isSameYear(first, last)) return `${format(first, 'd MMM')} – ${format(last, 'd MMM yyyy')}`
  return `${format(first, 'd MMM yyyy')} – ${format(last, 'd MMM yyyy')}`
}
