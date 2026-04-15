# PRD.md - Product Requirements Document

## 1. Product Overview

**Pixi** (robocza nazwa) to lekki, cross-platformowy system mikro-automatyzacji, który działa w tle i reaguje na skróty klawiszowe. Użytkownicy mogą definiować swoje workflowy, korzystając z zestawu gotowych narzędzi (tools) do transformacji, wizualizacji i interakcji z tekstem oraz kontekstem aplikacji.

### 1.1 Cel produktu

* Ułatwić szybkie i elastyczne automatyzacje w codziennej pracy.
* Zapewnić modularny system tooli, które można używać w wielu workflowach.
* Pozwolić na prostą personalizację przez użytkownika końcowego.

### 1.2 Kluczowe funkcje

* Globalny nasłuch skrótów klawiszowych (Linux, Windows).
* Core workflow engine i context builder.
* Zestaw gotowych tooli: popup, TTS, clipboard, AI, selector.
* Łatwe pisanie workflowów korzystających z tooli.
* Konfiguracja skrótów i workflowów w plikach YAML i Python.

### 1.3 Zakres użytkownika

* Pisanie własnych workflowów w Pythonie.
* Dostosowywanie konfiguracji skrótów.
* Wybór i modyfikacja dostępnych tooli.

---

# ARCHITECTURE.md - Architecture Overview

## 1. System Components

### 1.1 Core (cross-platform)

* **Engine:** Orkiestruje wywołania workflowów na podstawie kontekstu i triggerów.
* **Context Builder:** Buduje obiekt Context z danych systemowych i aplikacyjnych (zaznaczenie tekstu, clipboard, aktywna aplikacja).
* **Workflow Loader:** Dynamicznie ładuje workflowy z repozytorium użytkownika.
* **Tools Registry:** Centralne miejsce rejestracji tooli, zapewniające spójny interfejs dla workflowów.

### 1.2 OS Adapter / Event Listener

* **Linux:** Xlib / evdev / pynput do global hotkeys.
* **Windows:** pywin32 lub pynput dla global hotkeys.
* Forwarduje zdarzenia do Core Engine.

### 1.3 Runner / Daemon

* **Linux:** systemd service do uruchamiania przy starcie.
* **Windows:** Task Scheduler lub Windows Service.
* Minimalny footprint, działa w tle, opcjonalnie z tray icon.

## 2. Data Flow

1. Użytkownik naciska skrót globalny.
2. OS Adapter wykrywa skrót i przekazuje trigger do Engine.
3. Engine tworzy Context (np. zaznaczony tekst, clipboard, aplikacja).
4. Engine mapuje trigger → workflow.
5. Workflow wykorzystuje zarejestrowane Tools do wykonania operacji (popup, TTS, AI, itp.).
6. Rezultat jest prezentowany użytkownikowi lub zapisany do clipboard / notatki.

## 3. Tools Design

* **Philosophy:** proste, deterministyczne, maksymalnie przewidywalne.
* **Interfejs:** każdy tool ma spójny API i minimalny zestaw metod (np. `popup.show(text)`).
* **Walidacja wejścia:** Pydantic dla Python, by workflowy nie powodowały błędów.
* **Rozszerzalność:** użytkownik może dodawać nowe narzędzia w repo workflowów.

## 4. Workflow Design

* **Python classes** z metodą `run(context, tools)`.
* Wywołania tooli wewnątrz workflowów.
* Łatwe pisanie nowych workflowów bez ingerencji w core.
* Triggerowane przez konfigurację YAML (skrót → workflow).

## 5. Configuration

* **Pliki YAML:** definiują skróty klawiszowe i mapowania do workflowów.
* **Workflow Folder:** użytkownik dodaje własne workflowy w Pythonie.
* **Tools:** dostępne jako część repo; workflowy korzystają bez dodatkowej konfiguracji.

## 6. UI Primitives (Tools)

* **Popup** – okno przy kursorze.
* **AI** – wysyłanie zapytań i odbiór wyników.
* **Selector/Input Box** – interakcja z użytkownikiem.
* **question** – interakcja z użytkownikiem. proste pytanie i kilka przycisków na odpowiedź

## 7. Cross-platform Considerations

* OS-specific listener abstrahowany przez adapter.
* Core pozostaje w pełni niezależny od systemu.
* Tray i powiadomienia mają oddzielne implementacje per OS.

---

To daje Ci pełną podstawę do rozpoczęcia repo jako **template**, z jasnym podziałem między core, workflowy, tools i OS adapterami.
