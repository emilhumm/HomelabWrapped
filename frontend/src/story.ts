/**
 * The story: one card at a time, full screen. Click or tap the right side (or
 * press → / space) for the next card, the left side (←) for the previous one,
 * Esc to close. Wide screens get two columns per card; phones get one.
 */

import { LitElement, css, html, type PropertyValues, type TemplateResult } from "lit";
import { keyed } from "lit/directives/keyed.js";

import { Format } from "./format";
import { drawShareImage, shareOrDownload } from "./share";
import { renderSlide, renderSummary } from "./slides";
import { SHARE, STORY } from "./text";
import type { CardsResponse } from "./types";

export class HomelabWrappedStory extends LitElement {
  static properties = {
    data: { attribute: false },
    language: { type: String },
    _index: { state: true },
    _sharing: { state: true },
    _names: { state: true },
    _shareError: { state: true },
  };

  declare data: CardsResponse;
  declare language: string;
  declare _index: number;
  declare _sharing: boolean;
  declare _names: boolean;
  declare _shareError?: string;

  constructor() {
    super();
    this._index = 0;
    this._sharing = false;
    this._names = false;
    this.language = navigator.language;
  }

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this._onKey);
    // A dialog over the panel: screen readers stay in it.
    this.setAttribute("role", "dialog");
    this.setAttribute("aria-modal", "true");
  }

  protected firstUpdated(): void {
    this.setAttribute("aria-label", `${SHARE.brand} ${this.data.year}`);
    this.renderRoot.querySelector<HTMLButtonElement>("button.close")?.focus();
  }

  protected willUpdate(changed: PropertyValues<this>): void {
    // New cards (played again, or another year): start from the first one.
    if (changed.has("data") && changed.get("data") !== undefined) this._index = 0;
  }

  disconnectedCallback(): void {
    window.removeEventListener("keydown", this._onKey);
    super.disconnectedCallback();
  }

  private get _count(): number {
    return this.data.cards.length + 1; // the summary closes the story
  }

  private _onKey = (event: KeyboardEvent): void => {
    // Leave keys to the browser (Alt+← is back) and to text fields (HA's own dialogs); leave
    // Space and Enter to a focused button or checkbox; don't run through on key repeat.
    if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return;
    const target = event.composedPath()[0];
    if (target instanceof HTMLElement) {
      const field = target instanceof HTMLInputElement && !["checkbox", "radio", "button"].includes(target.type);
      if (target.isContentEditable || field || ["TEXTAREA", "SELECT"].includes(target.tagName)) return;
      const pressable = ["BUTTON", "A", "INPUT"].includes(target.tagName);
      if (pressable && (event.key === " " || event.key === "Enter")) return;
    }
    if (this._sharing) {
      if (event.key === "Escape") {
        this._sharing = false;
        event.preventDefault();
      }
      return;
    }
    if (event.key === "ArrowRight" || event.key === " ") this._go(1);
    else if (event.key === "ArrowLeft") this._go(-1);
    else if (event.key === "Escape") this._close();
    else return;
    event.preventDefault();
  };

  /** A click or tap on the slide: the left 30 % goes back, the rest forward. */
  private _tap = (event: MouseEvent): void => {
    const box = this.getBoundingClientRect();
    this._go(event.clientX - box.left < box.width * 0.3 ? -1 : 1);
  };

  private _go(step: number): void {
    const next = this._index + step;
    if (next >= this._count) this._close();
    else this._index = Math.max(0, next);
  }

  private _close(): void {
    this.dispatchEvent(new CustomEvent("close"));
  }

  protected updated(changed: PropertyValues<this>): void {
    if (changed.has("_sharing") && changed.get("_sharing") !== undefined) {
      // Into the share view, and back to the button that opened it.
      const target = this._sharing ? ".share-controls input" : ".end .pill.light";
      this.renderRoot.querySelector<HTMLElement>(target)?.focus();
    }
    const canvas = this.renderRoot.querySelector<HTMLCanvasElement>("canvas.share");
    if (canvas) drawShareImage(canvas, this.data, { names: this._names }, this.language);
  }

  private async _save(): Promise<void> {
    const canvas = this.renderRoot.querySelector<HTMLCanvasElement>("canvas.share");
    if (!canvas) return;
    this._shareError = undefined;
    try {
      await shareOrDownload(canvas, this.data.year);
    } catch (err) {
      if ((err as Error)?.name !== "AbortError") this._shareError = SHARE.failed;
    }
  }

  private _renderShare(): TemplateResult {
    return html`
      <div class="share-view" role="dialog" aria-label=${SHARE.title}>
        <canvas class="share"></canvas>
        <div class="share-controls">
          <label>
            <input
              type="checkbox"
              .checked=${this._names}
              @change=${(event: Event) => (this._names = (event.target as HTMLInputElement).checked)}
            />
            ${SHARE.names}
          </label>
          <p class="share-hint">${SHARE.namesHint}</p>
          ${this._shareError ? html`<p class="share-hint">${this._shareError}</p>` : ""}
          <div class="share-buttons">
            <button class="pill light" @click=${this._save}>${SHARE.save}</button>
            <button class="pill" @click=${() => (this._sharing = false)}>${SHARE.back}</button>
          </div>
        </div>
      </div>
    `;
  }

  protected render(): TemplateResult {
    const f = new Format(this.language);
    const { cards, year } = this.data;
    const last = this._index === this._count - 1;
    return html`
      <div class="shade"></div>
      <div class="progress">
        ${Array.from({ length: this._count }, (_, n) => html`<i class=${n <= this._index ? "seen" : ""}></i>`)}
      </div>
      <button class="close" aria-label=${STORY.close} ?inert=${this._sharing} @click=${this._close}>✕</button>
      <div class="stage" aria-live="polite" ?inert=${this._sharing} @click=${this._tap}>
        ${
          // A new element for each slide: it starts at its top (not where the last one was
          // scrolled to) and fades in.
          keyed(this._index, last ? renderSummary(cards, year, f) : renderSlide(cards[this._index], year, f))
        }
      </div>
      <button
        class="nav previous"
        aria-label=${STORY.previous}
        ?inert=${this._sharing}
        @click=${() => this._go(-1)}
      ></button>
      <button
        class="nav next"
        aria-label=${last ? STORY.done : STORY.next}
        ?inert=${this._sharing}
        @click=${() => this._go(1)}
      ></button>
      ${last
        ? html`<div class="end" ?inert=${this._sharing}>
            <button class="pill light" @click=${() => (this._sharing = true)}>${SHARE.button}</button>
            <button class="pill" @click=${this._close}>${STORY.done}</button>
          </div>`
        : ""}
      ${this._sharing ? this._renderShare() : ""}
    `;
  }

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      z-index: 10;
      display: block;
      color: #fff;
      font-family: var(--paper-font-body1_-_font-family, Roboto, "Segoe UI", sans-serif);
      background: #111827;
    }
    /* Behind the progress bar and the close button: they stay readable over a slide
       that scrolls under them. */
    .shade {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      z-index: 2;
      height: 64px;
      background: linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0));
      pointer-events: none;
    }
    .progress {
      position: absolute;
      top: 12px;
      left: 16px;
      right: 64px;
      z-index: 3;
      display: flex;
      gap: 6px;
    }
    .progress i {
      flex: 1;
      height: 4px;
      border-radius: 2px;
      background: rgba(255, 255, 255, 0.3);
    }
    .progress i.seen {
      background: #fff;
    }
    button {
      font: inherit;
      color: inherit;
      cursor: pointer;
    }
    .close {
      position: absolute;
      top: 4px;
      right: 8px;
      z-index: 4;
      width: 48px;
      height: 48px;
      border: 0;
      background: none;
      font-size: 22px;
    }
    /* For keyboards and screen readers. Clicks and taps land on the slide itself, so a
       slide taller than the screen still scrolls under a finger or a mouse wheel. */
    .nav {
      position: absolute;
      top: 48px;
      bottom: 0;
      z-index: 2;
      border: 0;
      background: none;
      padding: 0;
      pointer-events: none;
    }
    .nav.previous {
      left: 0;
      width: 30%;
    }
    .nav.next {
      right: 0;
      width: 70%;
    }
    .nav:focus-visible,
    .close:focus-visible,
    .pill:focus-visible {
      outline: 2px solid #fff;
      outline-offset: 2px;
    }
    .end {
      position: absolute;
      bottom: 32px;
      left: 0;
      right: 0;
      z-index: 4;
      display: flex;
      justify-content: center;
      gap: 12px;
    }
    .pill {
      padding: 12px 28px;
      border-radius: 999px;
      border: 2px solid #fff;
      background: transparent;
      font-weight: 600;
    }
    .pill.light {
      background: #fff;
      color: #111827;
    }
    .share-view {
      position: absolute;
      inset: 0;
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      padding: 24px;
      background: rgba(10, 10, 20, 0.92);
    }
    canvas.share {
      height: min(86vh, 960px);
      max-width: 46vw;
      aspect-ratio: 9 / 16;
      object-fit: contain;
      border-radius: 16px;
      box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
    }
    .share-controls {
      max-width: 340px;
    }
    .share-controls label {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 18px;
      cursor: pointer;
    }
    .share-controls input {
      width: 20px;
      height: 20px;
    }
    .share-hint {
      margin-top: 8px;
      font-size: 14px;
      opacity: 0.75;
    }
    .share-buttons {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
    .stage {
      position: absolute;
      inset: 0;
    }

    /* A slide: text and a picture side by side on wide screens, stacked on phones. */
    .slide {
      box-sizing: border-box;
      height: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      align-items: center;
      gap: 48px;
      padding: 72px clamp(24px, 6vw, 96px) 48px;
      overflow: auto;
      animation: appear 0.35s ease-out;
    }
    @keyframes appear {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .slide {
        animation: none;
      }
    }
    .intro {
      background: linear-gradient(135deg, #312e81, #6d28d9);
    }
    .uptime {
      background: linear-gradient(135deg, #064e3b, #0f766e);
    }
    .restarts {
      background: linear-gradient(135deg, #7c2d12, #c2410c);
    }
    .blocked {
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
    }
    .media {
      background: linear-gradient(135deg, #701a75, #be185d);
    }
    .power {
      background: linear-gradient(135deg, #713f12, #a16207);
    }
    .power .column i {
      background: #fde047;
    }
    .personality {
      background: linear-gradient(135deg, #134e4a, #4338ca);
    }
    .icon {
      display: flex;
      justify-content: center;
      --mdc-icon-size: clamp(140px, 22vw, 320px);
      color: rgba(255, 255, 255, 0.92);
    }
    .who {
      display: flex;
      align-items: center;
      gap: 10px;
      --mdc-icon-size: 1.3em;
    }
    .summary {
      background: linear-gradient(135deg, #111827, #374151);
    }
    p {
      margin: 0 0 12px;
      font-size: clamp(16px, 1.6vw, 22px);
      line-height: 1.4;
    }
    .kicker {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 14px;
      font-weight: 600;
      opacity: 0.85;
    }
    .hero {
      margin: 0 0 0.12em;
      font-size: clamp(56px, 9vw, 140px);
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.03em;
    }
    .title {
      margin: 0 0 16px;
      font-size: clamp(32px, 4.5vw, 64px);
      font-weight: 800;
      line-height: 1.05;
    }
    .line {
      font-size: clamp(18px, 2vw, 28px);
      font-weight: 500;
    }
    .fact,
    .sub {
      opacity: 0.9;
    }
    .sub {
      margin-top: 20px;
      font-weight: 600;
    }
    .note {
      margin-top: 24px;
      font-size: 14px;
      opacity: 0.75;
    }
    .early {
      display: inline-block;
      margin-left: 8px;
      padding: 2px 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.18);
    }
    .list {
      list-style: none;
      margin: 0;
      padding: 0;
      max-width: 420px;
    }
    .list li {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    }
    /* A long container or title wraps instead of pushing its number off a phone's screen. */
    .list li span {
      min-width: 0;
      overflow-wrap: anywhere;
    }
    /* A name without break points (a container's) wraps instead of running out. */
    .slide p {
      overflow-wrap: anywhere;
    }
    .list li b {
      flex: none;
    }
    .tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
    }
    .tile {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 20px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.12);
      /* The number is sized by its tile, not the window: five tiles in a row on a wide
         screen are narrow, and "456,789" must still fit. */
      container-type: inline-size;
    }
    .tile b {
      font-size: clamp(28px, 22cqi, 56px);
      font-weight: 800;
      line-height: 1;
      white-space: nowrap;
    }
    /* "5,2 mio." and the like: smaller, so it stays in its tile. */
    .tile b.long {
      font-size: clamp(22px, 15cqi, 38px);
    }

    /* Uptime: the year, one square per day, a column per week. */
    .year {
      margin: 0;
    }
    .year figcaption {
      margin-bottom: 12px;
      font-weight: 600;
    }
    .grid {
      display: grid;
      grid-auto-flow: column;
      grid-template-rows: repeat(7, auto);
      grid-auto-columns: minmax(0, 1fr);
      gap: 3px;
    }
    .grid i,
    .legend i {
      display: block;
      aspect-ratio: 1;
      border-radius: 2px;
    }
    .up {
      background: #34d399;
    }
    .r1 {
      background: #fde68a;
    }
    .r2 {
      background: #fbbf24;
    }
    .r3 {
      background: #f97316;
    }
    .none {
      background: rgba(255, 255, 255, 0.12);
    }
    .pad {
      visibility: hidden;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 20px;
      margin-top: 12px;
      font-size: 13px;
      opacity: 0.9;
    }
    .legend span {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .legend i {
      width: 12px;
    }
    .legend .scale {
      display: flex;
      gap: 2px;
    }
    .legend .weekdays {
      margin-left: auto;
      opacity: 0.7;
    }

    /* Restarts: one bar per machine. */
    .bars {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 14px;
    }
    .bars li {
      display: grid;
      grid-template-columns: minmax(80px, 30%) 1fr auto;
      align-items: center;
      gap: 12px;
      font-size: 18px;
    }
    .bars .name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bars b {
      /* The same width in every row, so the bars end in one line. */
      min-width: 3ch;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .bar {
      height: 14px;
      border-radius: 7px;
      background: rgba(255, 255, 255, 0.15);
      overflow: hidden;
    }
    .bar i {
      display: block;
      height: 100%;
      min-width: 4px;
      border-radius: 7px;
      background: #fde68a;
    }

    /* Blocked. */
    .shield svg {
      width: min(320px, 60%);
      display: block;
      margin: auto;
      fill: rgba(255, 255, 255, 0.85);
    }

    /* Media: hours per month. */
    .months {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 8px;
      height: min(360px, 50vh);
    }
    .month {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .column {
      flex: 1;
      display: flex;
      align-items: flex-end;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.1);
    }
    .column i {
      display: block;
      width: 100%;
      border-radius: 6px;
      background: #f9a8d4;
    }
    .month.none .column {
      background: rgba(255, 255, 255, 0.04);
    }
    .label {
      font-size: 12px;
      text-align: center;
      opacity: 0.85;
    }

    @media (max-width: 800px) {
      /* Centred while it fits; a slide taller than the screen starts at its top and scrolls
         (auto margins work everywhere, unlike "safe center" on older Safari). */
      .slide {
        display: flex;
        flex-direction: column;
        /* The wide layout centres its two columns; here each block takes the full width. */
        align-items: stretch;
        gap: 28px;
        padding: 64px 20px 96px;
      }
      .slide > * {
        min-width: 0;
      }
      .slide > :first-child {
        margin-top: auto;
      }
      .slide > :last-child {
        margin-bottom: auto;
      }
      .bars li {
        font-size: 15px;
      }
      /* Two tiles a row on any phone; their numbers are sized by the tile. */
      .tiles {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .months {
        height: 180px;
        gap: 4px;
      }
      .legend .weekdays {
        margin-left: 0;
      }
      .share-view {
        flex-direction: column;
        justify-content: flex-start;
        gap: 16px;
        overflow-y: auto;
      }
      canvas.share {
        flex: none;
        height: auto;
        width: min(78vw, 40vh);
        max-width: none;
      }
    }
  `;
}

if (!customElements.get("homelab-wrapped-story")) {
  customElements.define("homelab-wrapped-story", HomelabWrappedStory);
}
