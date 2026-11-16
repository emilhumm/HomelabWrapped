/**
 * The Homelab Wrapped sidebar panel: the coverage check (which cards this lab
 * can make today, and what would unlock the rest) and the button that plays a
 * year's story, with a choice of year once there is more than one.
 * Wide layout (monitor, wall tablet) first; it folds to one column on a phone.
 */

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import "./story";
import { CARDS, HINTS, STORY, TEXT, useLanguage } from "./text";
import type { CardCoverage, CardsResponse, Coverage, HomeAssistant } from "./types";

/** While Home Assistant starts, the panel can be there before Wrapped: check again for 2 minutes. */
const RETRY_SECONDS = 3;
const RETRIES = 40;

class HomelabWrappedPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    _coverage: { state: true },
    _error: { state: true },
    _toast: { state: true },
    _story: { state: true },
    _wrapping: { state: true },
    _year: { state: true },
  };

  declare hass?: HomeAssistant;
  declare narrow: boolean;
  declare _coverage?: Coverage;
  declare _error?: string;
  declare _toast?: string;
  declare _story?: CardsResponse;
  declare _wrapping: boolean;
  /** The year picked to play; the coverage report's suggestion until one is picked. */
  declare _year?: number;

  private _loading = false;
  private _toastTimer?: number;
  private _retryTimer?: number;
  private _retries = 0;

  constructor() {
    super();
    this.narrow = false;
    this._wrapping = false;
  }

  protected updated(changed: PropertyValues<this>): void {
    if (changed.has("hass") && this.hass && !this._coverage && !this._error && !this._loading) {
      void this._load();
    }
  }

  private _closeStory(): void {
    this._story = undefined;
    // Back where the story was opened from, for keyboards and screen readers.
    void this.updateComplete.then(() => this.renderRoot.querySelector<HTMLButtonElement>(".play")?.focus());
  }

  private _checkAgain(): void {
    this._retries = 0;
    void this._load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.clearTimeout(this._retryTimer);
    window.clearTimeout(this._toastTimer);
    // HA detaches a panel it hides for a while: check again when it's back.
    if (!this._coverage) this._loading = false;
  }

  private async _load(): Promise<void> {
    if (!this.hass) return;
    window.clearTimeout(this._retryTimer);
    this._loading = true;
    this._error = undefined;
    let retrying = false;
    try {
      const coverage = await this.hass.callWS<Coverage>({ type: "homelab_wrapped/coverage" });
      if (this._year === undefined || !coverage.years.includes(this._year)) this._year = coverage.year;
      this._coverage = coverage;
      this._retries = 0;
    } catch (err) {
      // Opened while Home Assistant is still starting (right after installing, say): the
      // panel is there before Wrapped is set up. Keep checking for a while instead of failing.
      if ((err as { code?: string })?.code === "not_found" && this._retries < RETRIES) {
        this._retries += 1;
        this._retryTimer = window.setTimeout(() => void this._load(), RETRY_SECONDS * 1000);
        retrying = true;
        return;
      }
      this._error = err instanceof Error ? err.message : String((err as { message?: string })?.message ?? err);
    } finally {
      this._loading = retrying;
    }
  }

  private async _copyDiagnostics(): Promise<void> {
    if (!this.hass) return;
    try {
      const report = await this.hass.callWS<unknown>({ type: "homelab_wrapped/diagnostics" });
      await copyText(JSON.stringify(report, null, 2));
      this._showToast(TEXT.copied);
    } catch {
      this._showToast(TEXT.copyFailed);
    }
  }

  private async _play(): Promise<void> {
    if (!this.hass || this._wrapping) return;
    this._wrapping = true;
    try {
      const story = await this.hass.callWS<CardsResponse>({ type: "homelab_wrapped/cards", year: this._year });
      if (story.cards.length) this._story = story;
      else this._showToast(STORY.noCards);
    } catch (err) {
      console.error("Homelab Wrapped: couldn't load the cards", err);
      this._showToast(TEXT.storyFailed(String((err as { message?: string })?.message ?? err)), 15);
    } finally {
      this._wrapping = false;
    }
  }

  private get _language(): string {
    return this.hass?.locale?.language ?? this.hass?.language ?? navigator.language;
  }

  /** A short note; errors stay up longer, so they can be read and reported. */
  private _showToast(message: string, seconds = 4): void {
    this._toast = message;
    window.clearTimeout(this._toastTimer);
    this._toastTimer = window.setTimeout(() => (this._toast = undefined), seconds * 1000);
  }

  private _date(iso: string): string {
    // "30 Nov", and "30 Nov 2025" when it's another year's.
    const day = new Date(`${iso}T00:00:00`);
    const year = day.getFullYear() === new Date().getFullYear() ? undefined : "numeric";
    return day.toLocaleDateString(this._language, { day: "numeric", month: "short", year });
  }

  protected render(): TemplateResult {
    useLanguage(this._language);
    const cards = this._coverage?.cards ?? [];
    const ready = cards.filter((card) => card.state === "ready").length;
    const playable = cards.some((card) => card.number <= 6 && card.state !== "locked");
    const year = this._year ?? new Date().getFullYear();
    const years = this._coverage?.years ?? [];
    return html`
      <div class="toolbar">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <div class="title">${TEXT.title}</div>
      </div>
      <main ?inert=${Boolean(this._story)}>
        <header>
          <h1>${TEXT.heading}</h1>
          ${this._coverage ? html`<p class="count">${TEXT.readyCount(ready, cards.length)}</p>` : nothing}
        </header>
        ${playable
          ? html`<button class="play" ?disabled=${this._wrapping} @click=${this._play}>
              ${this._wrapping ? STORY.loadingCards : STORY.play(year)}
            </button>`
          : nothing}
        ${playable && years.length > 1
          ? html`<div class="years" role="group" aria-label=${STORY.years}>
              ${[...years].reverse().map(
                (option) => html`<button
                  class=${option === year ? "year on" : "year"}
                  aria-pressed=${option === year ? "true" : "false"}
                  @click=${() => (this._year = option)}
                >
                  ${option}
                </button>`,
              )}
            </div>`
          : nothing}
        ${this._error
          ? html`<p class="error">${TEXT.failed(this._error)}</p>`
          : this._coverage
            ? html`<section class="grid">${cards.map((card) => this._renderCard(card))}</section>`
            : html`<p class="muted">${TEXT.loading}</p>`}
        <footer>
          <button class="primary" @click=${this._copyDiagnostics}>${TEXT.copy}</button>
          <button @click=${this._checkAgain}>${TEXT.refresh}</button>
          <span class="muted">${TEXT.privacy}</span>
        </footer>
      </main>
      ${this._toast ? html`<div class="toast" role="status">${this._toast}</div>` : nothing}
      ${this._story
        ? html`<homelab-wrapped-story
            .data=${this._story}
            .language=${this._language}
            @close=${this._closeStory}
          ></homelab-wrapped-story>`
        : nothing}
    `;
  }

  private _renderCard(card: CardCoverage): TemplateResult {
    const text = CARDS[card.card];
    return html`
      <article class=${card.state}>
        <div class="top">
          <span class="number">${String(card.number).padStart(2, "0")}</span>
          <span class="chip">${TEXT[card.state]}</span>
        </div>
        <h2>${text.title}</h2>
        <p class="about">${text.about}</p>
        <p class="status">${this._status(card)}</p>
        ${card.hints.map((hint) => html`<p class="hint">${HINTS[hint]}</p>`)}
      </article>
    `;
  }

  private _status(card: CardCoverage): string {
    const derived = card.card === "personality" || card.card === "summary";
    switch (card.state) {
      case "ready":
        if (card.since) {
          const since = TEXT.since(this._date(card.since));
          return card.sources.length ? `${since} · ${TEXT.from(card.sources.join(", "))}` : since;
        }
        return card.sources.length ? TEXT.from(card.sources.join(", ")) : TEXT.builtFromOthers;
      case "counting": {
        const parts = [card.ready_on ? TEXT.readyOn(this._date(card.ready_on)) : ""];
        if (card.since) parts.push(TEXT.collectingSince(this._date(card.since)));
        return parts.filter(Boolean).join(" · ");
      }
      case "locked":
        if (card.unlock.length) {
          return TEXT.connect(new Intl.ListFormat(this._language, { type: "disjunction" }).format(card.unlock));
        }
        return derived ? TEXT.builtFromOthers : "";
    }
  }

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--paper-font-body1_-_font-family, inherit);
    }
    .toolbar {
      display: flex;
      align-items: center;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color));
      font-size: 20px;
    }
    .title {
      margin-left: 12px;
    }
    main {
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px 16px 96px;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px 24px;
      margin-bottom: 20px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 500;
    }
    .count {
      margin: 0;
      color: var(--secondary-text-color);
      font-size: 18px;
    }
    .play {
      display: block;
      width: 100%;
      margin: 0 0 24px;
      padding: 20px 24px;
      border: 0;
      border-radius: var(--ha-card-border-radius, 12px);
      background: linear-gradient(135deg, #312e81, #6d28d9 55%, #be185d);
      color: #fff;
      font-size: 22px;
      font-weight: 700;
      text-align: left;
    }
    .play:disabled {
      opacity: 0.7;
      cursor: progress;
    }
    .years {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: -12px 0 24px;
    }
    .year {
      padding: 6px 16px;
      border: 1px solid var(--divider-color);
      border-radius: 999px;
      background: none;
      color: inherit;
      font: inherit;
      cursor: pointer;
    }
    .year.on {
      border-color: transparent;
      background: var(--primary-color);
      color: var(--text-primary-color);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }
    article {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 16px 18px;
      border-radius: var(--ha-card-border-radius, 12px);
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-left: 4px solid var(--state-color);
    }
    article.ready {
      --state-color: var(--success-color, #43a047);
    }
    article.counting {
      --state-color: var(--warning-color, #ffa600);
    }
    article.locked {
      --state-color: var(--disabled-text-color, #9e9e9e);
    }
    article.locked h2,
    article.locked .about {
      color: var(--secondary-text-color);
    }
    .top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .number {
      font-variant-numeric: tabular-nums;
      color: var(--secondary-text-color);
    }
    .chip {
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      color: var(--state-color);
      border: 1px solid var(--state-color);
    }
    h2 {
      margin: 4px 0 0;
      font-size: 20px;
      font-weight: 500;
    }
    p {
      margin: 0;
    }
    .about {
      color: var(--secondary-text-color);
    }
    .status {
      margin-top: auto;
      padding-top: 8px;
      font-size: 14px;
    }
    .hint {
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .muted {
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color, #db4437);
    }
    footer {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
      margin-top: 24px;
    }
    button {
      font: inherit;
      padding: 8px 16px;
      border-radius: 8px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      cursor: pointer;
    }
    button.primary {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
    .toast {
      position: fixed;
      left: 50%;
      bottom: 24px;
      transform: translateX(-50%);
      width: max-content;
      max-width: calc(100vw - 32px);
      box-sizing: border-box;
      padding: 12px 20px;
      border-radius: 8px;
      background: var(--primary-text-color);
      color: var(--primary-background-color);
    }
    @media (max-width: 600px) {
      main {
        padding-top: 16px;
      }
      h1 {
        font-size: 22px;
      }
      .grid {
        grid-template-columns: 1fr;
      }
    }
  `;
}

/** Copy text; over plain http (common on a LAN) the Clipboard API isn't there, so fall back. */
async function copyText(text: string): Promise<void> {
  if (window.isSecureContext && navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.append(area);
  area.select();
  const copied = document.execCommand("copy");
  area.remove();
  if (!copied) throw new Error("copy failed");
}

if (!customElements.get("homelab-wrapped-panel")) {
  customElements.define("homelab-wrapped-panel", HomelabWrappedPanel);
}
