import { addDays, differenceInMinutes, startOfDay, startOfWeek } from 'date-fns'

import type { Meeting } from '@/lib/api'

export type ViewMode = 'list' | 'day' | 'week'

const MINUTES_PER_DAY = 24 * 60

/** Days shown by a view: the list is the anchor ±3 days, the week starts on Monday. */
export function visibleDays(mode: ViewMode, anchor: Date): Date[] {
  const day = startOfDay(anchor)
  if (mode === 'day') return [day]
  const first = mode === 'list' ? addDays(day, -3) : startOfWeek(day, { weekStartsOn: 1 })
  return Array.from({ length: 7 }, (_, i) => addDays(first, i))
}

/** How far the prev/next buttons move the anchor. */
export const STEP_DAYS: Record<ViewMode, number> = { list: 7, day: 1, week: 7 }

/** Meetings that overlap the given local day (multi-day meetings appear on every day they touch). */
export function meetingsOnDay(meetings: Meeting[], day: Date): Meeting[] {
  const dayStart = startOfDay(day)
  const dayEnd = addDays(dayStart, 1)
  return meetings.filter((m) => new Date(m.starts_at) < dayEnd && new Date(m.ends_at) > dayStart)
}

export type PositionedMeeting = {
  meeting: Meeting
  /** Minutes since the start of the day, clipped to the day. */
  startMin: number
  endMin: number
  /** The meeting continues from the previous day / into the next day. */
  continuesBefore: boolean
  continuesAfter: boolean
  /** Side-by-side column within a group of overlapping meetings. */
  lane: number
  lanes: number
}

/** Places a day's meetings on a time grid; overlapping meetings share the width in lanes. */
export function layoutDay(meetings: Meeting[], day: Date): PositionedMeeting[] {
  const dayStart = startOfDay(day)
  const items: PositionedMeeting[] = meetingsOnDay(meetings, day)
    .map((meeting) => {
      const start = differenceInMinutes(new Date(meeting.starts_at), dayStart)
      const end = differenceInMinutes(new Date(meeting.ends_at), dayStart)
      return {
        meeting,
        startMin: Math.max(0, start),
        endMin: Math.min(MINUTES_PER_DAY, end),
        continuesBefore: start < 0,
        continuesAfter: end > MINUTES_PER_DAY,
        lane: 0,
        lanes: 1,
      }
    })
    .sort((a, b) => a.startMin - b.startMin || b.endMin - a.endMin)

  let group: PositionedMeeting[] = []
  let laneEnds: number[] = []
  let groupEnd = -1
  const closeGroup = () => {
    for (const item of group) item.lanes = laneEnds.length
    group = []
    laneEnds = []
  }

  for (const item of items) {
    if (item.startMin >= groupEnd) closeGroup()
    let lane = laneEnds.findIndex((end) => end <= item.startMin)
    if (lane === -1) lane = laneEnds.length
    laneEnds[lane] = item.endMin
    item.lane = lane
    group.push(item)
    groupEnd = Math.max(groupEnd, item.endMin)
  }
  closeGroup()

  return items
}
