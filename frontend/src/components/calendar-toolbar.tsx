import {
  CalendarDaysIcon,
  CalendarIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ListIcon,
} from 'lucide-react'
import { ToggleGroup } from 'radix-ui'

import { Button } from '@/components/ui/button'
import type { ViewMode } from '@/lib/calendar'

const VIEWS: { value: ViewMode; label: string; icon: typeof ListIcon }[] = [
  { value: 'list', label: 'List', icon: ListIcon },
  { value: 'day', label: 'Day', icon: CalendarIcon },
  { value: 'week', label: 'Week', icon: CalendarDaysIcon },
]

export function ViewSwitcher({
  mode,
  onModeChange,
}: {
  mode: ViewMode
  onModeChange: (mode: ViewMode) => void
}) {
  return (
    <ToggleGroup.Root
      type="single"
      value={mode}
      // Radix sends "" when the active item is clicked again; keep the current view.
      onValueChange={(value) => value && onModeChange(value as ViewMode)}
      aria-label="View"
      className="inline-flex rounded-full bg-card p-1"
    >
      {VIEWS.map(({ value, label, icon: Icon }) => (
        <ToggleGroup.Item
          key={value}
          value={value}
          aria-label={label}
          title={label}
          className="inline-flex h-8 items-center gap-2 rounded-full px-2.5 text-sm sm:px-3.5 font-semibold text-muted-foreground transition-colors outline-none hover:text-hover focus-visible:ring-3 focus-visible:ring-ring/50 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground [&_svg]:size-4"
        >
          <Icon />
          <span className="max-sm:hidden">{label}</span>
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  )
}

type Props = {
  rangeLabel: string
  onPrev: () => void
  onNext: () => void
  onToday: () => void
}

/** Today ‹ › and the visible range, Google Calendar style. */
export function DateNavigation({ rangeLabel, onPrev, onNext, onToday }: Props) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <Button variant="outline" size="sm" onClick={onToday}>
        Today
      </Button>
      <div className="flex items-center">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Previous"
          title="Previous"
          onClick={onPrev}
        >
          <ChevronLeftIcon />
        </Button>
        <Button variant="ghost" size="icon-sm" aria-label="Next" title="Next" onClick={onNext}>
          <ChevronRightIcon />
        </Button>
      </div>
      <p
        className="truncate font-serif text-xl font-medium text-heading md:text-2xl"
        aria-live="polite"
      >
        {rangeLabel}
      </p>
    </div>
  )
}
