import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useDeleteMeeting } from '@/hooks/queries'
import type { Meeting } from '@/lib/api'

type Props = {
  meeting: Meeting | null
  onClose: () => void
}

export function DeleteMeetingDialog({ meeting, onClose }: Props) {
  const deleteMeeting = useDeleteMeeting()

  const confirm = (event: React.MouseEvent) => {
    event.preventDefault()
    if (!meeting) return
    deleteMeeting.mutate(meeting.id, {
      onSuccess: () => {
        toast.success(`Meeting "${meeting.title}" deleted`)
        onClose()
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <AlertDialog open={meeting !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete meeting &ldquo;{meeting?.title}&rdquo;?</AlertDialogTitle>
          <AlertDialogDescription>This cannot be undone.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteMeeting.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={confirm}
            disabled={deleteMeeting.isPending}
          >
            {deleteMeeting.isPending ? 'Deleting...' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
