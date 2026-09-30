import { useState } from 'react'
import { CheckIcon, ChevronsUpDownIcon, PlusIcon, XIcon } from 'lucide-react'
import { toast } from 'sonner'
import { z } from 'zod'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import { Field, FieldError, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useCreateParticipant, useParticipants } from '@/hooks/queries'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

const newParticipantSchema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(100),
  email: z.email('Enter a valid email').max(255),
})

type Props = {
  id?: string
  value: string[]
  onChange: (value: string[]) => void
  invalid?: boolean
}

export function ParticipantPicker({ id, value, onChange, invalid }: Props) {
  const [open, setOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const participants = useParticipants()
  const selected = (participants.data ?? []).filter((p) => value.includes(p.id))

  const toggle = (participantId: string) =>
    onChange(
      value.includes(participantId)
        ? value.filter((v) => v !== participantId)
        : [...value, participantId],
    )

  return (
    <div className="flex flex-col gap-2">
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setCreating(false)
        }}
      >
        <PopoverTrigger asChild>
          <Button
            id={id}
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            aria-invalid={invalid}
            className="w-full justify-between font-normal"
          >
            <span className="text-muted-foreground">
              {value.length ? `${value.length} selected` : 'Select participants'}
            </span>
            <ChevronsUpDownIcon className="opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
          {creating ? (
            <NewParticipantForm
              onCancel={() => setCreating(false)}
              onCreated={(participantId) => {
                onChange([...value, participantId])
                setCreating(false)
              }}
            />
          ) : (
            <Command>
              <CommandInput placeholder="Search participants..." />
              <CommandList>
                <CommandEmpty>
                  {participants.isLoading ? 'Loading...' : 'No participants found.'}
                </CommandEmpty>
                <CommandGroup>
                  {participants.data?.map((p) => (
                    <CommandItem
                      key={p.id}
                      value={`${p.name} ${p.email}`}
                      onSelect={() => toggle(p.id)}
                    >
                      <CheckIcon
                        className={cn(value.includes(p.id) ? 'opacity-100' : 'opacity-0')}
                      />
                      <div className="flex flex-col">
                        <span>{p.name}</span>
                        <span className="text-xs text-muted-foreground">{p.email}</span>
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
              <CommandSeparator />
              <CommandGroup forceMount>
                <CommandItem forceMount onSelect={() => setCreating(true)}>
                  <PlusIcon />
                  New participant
                </CommandItem>
              </CommandGroup>
            </Command>
          )}
        </PopoverContent>
      </Popover>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((p) => (
            <Badge key={p.id} variant="secondary" className="gap-1 pr-1">
              {p.name}
              <button
                type="button"
                aria-label={`Remove ${p.name}`}
                className="rounded-sm opacity-60 hover:opacity-100"
                onClick={() => toggle(p.id)}
              >
                <XIcon className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

// Rendered inside a portal, but React still bubbles submit events to the
// meeting form, so this deliberately avoids a nested <form>.
function NewParticipantForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void
  onCreated: (participantId: string) => void
}) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState<{ name?: string; email?: string }>({})
  const createParticipant = useCreateParticipant()

  const submit = () => {
    const parsed = newParticipantSchema.safeParse({ name, email })
    if (!parsed.success) {
      const fieldErrors = z.flattenError(parsed.error).fieldErrors
      setErrors({ name: fieldErrors.name?.[0], email: fieldErrors.email?.[0] })
      return
    }
    setErrors({})
    createParticipant.mutate(parsed.data, {
      onSuccess: (participant) => {
        toast.success(`Added ${participant.name}`)
        onCreated(participant.id)
      },
      onError: (error) => {
        if (error instanceof ApiError && error.status === 409) {
          setErrors({ email: error.message })
        } else {
          toast.error(error.message)
        }
      },
    })
  }

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex flex-col gap-3 p-3" onKeyDown={onKeyDown}>
      <p className="text-sm font-medium">New participant</p>
      <Field data-invalid={!!errors.name}>
        <FieldLabel htmlFor="new-participant-name">Name</FieldLabel>
        <Input
          id="new-participant-name"
          autoFocus
          value={name}
          aria-invalid={!!errors.name}
          onChange={(e) => setName(e.target.value)}
        />
        <FieldError>{errors.name}</FieldError>
      </Field>
      <Field data-invalid={!!errors.email}>
        <FieldLabel htmlFor="new-participant-email">Email</FieldLabel>
        <Input
          id="new-participant-email"
          type="email"
          value={email}
          aria-invalid={!!errors.email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FieldError>{errors.email}</FieldError>
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" size="sm" onClick={submit} disabled={createParticipant.isPending}>
          Add
        </Button>
      </div>
    </div>
  )
}
