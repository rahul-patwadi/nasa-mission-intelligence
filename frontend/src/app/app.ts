import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { SourceItem } from './models/ntrs-api.models';
import { NtrsApiService } from './services/ntrs-api.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: SourceItem[];
}

const ALL_MISSIONS_OPTION = 'All';

const SUGGESTIONS: readonly string[] = [
  'What were the main goals of the Apollo program?',
  'How does the ISS handle life support?',
  'What did Voyager discover about the outer planets?',
  'What challenges does Artemis face for lunar landings?',
];

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private readonly messageList = viewChild<ElementRef<HTMLDivElement>>('messageList');

  private readonly composerInput = viewChild<ElementRef<HTMLTextAreaElement>>('composerInput');

  readonly suggestions = SUGGESTIONS;
  readonly missionOptions = signal<string[]>([ALL_MISSIONS_OPTION]);
  readonly selectedMission = signal<string>(ALL_MISSIONS_OPTION);
  readonly messages = signal<ChatMessage[]>([]);
  readonly questionInput = signal<string>('');
  readonly loading = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  constructor(private readonly api: NtrsApiService) {}

  ngOnInit(): void {
    this.api.getMissions().subscribe({
      next: (response) => {
        this.missionOptions.set([ALL_MISSIONS_OPTION, ...response.missions]);
      },
      error: () => {
        // Keep the static "All" option so the chat still works if this call fails.
      },
    });
  }

  send(): void {
    const question = this.questionInput().trim();
    if (!question || this.loading()) {
      return;
    }

    this.messages.update((messages) => [...messages, { role: 'user', text: question }]);
    this.questionInput.set('');
    this.resetComposerHeight();
    this.error.set(null);
    this.loading.set(true);
    this.scrollToBottom();

    const missionFilter = this.selectedMission() === ALL_MISSIONS_OPTION ? null : this.selectedMission();

    this.api.query({ question, mission_filter: missionFilter }).subscribe({
      next: (response) => {
        this.messages.update((messages) => [
          ...messages,
          { role: 'assistant', text: response.answer, sources: response.sources },
        ]);
        this.loading.set(false);
        this.scrollToBottom();
      },
      error: () => {
        this.error.set('Something went wrong while getting a response. Please try again.');
        this.loading.set(false);
      },
    });
  }

  useSuggestion(suggestion: string): void {
    this.questionInput.set(suggestion);
    this.send();
  }

  autoGrow(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = `${textarea.scrollHeight}px`;
  }

  onInputKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  private resetComposerHeight(): void {
    const textarea = this.composerInput()?.nativeElement;
    if (textarea) {
      textarea.style.height = 'auto';
    }
  }

  private scrollToBottom(): void {
    queueMicrotask(() => {
      const el = this.messageList()?.nativeElement;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }
}
