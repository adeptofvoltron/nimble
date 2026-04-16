---
title: "Product Brief: Nimble"
status: "complete"
created: "2026-04-15"
updated: "2026-04-15"
inputs:
  - docs/scratchprd.md
  - docs/unorganisedIdeas.md
---

# Product Brief: Nimble

## Executive Summary

Every developer has had the moment: you're deep in a task, you need to translate a phrase, ask a quick AI question, or reformat a clipboard snippet — and suddenly you're tabbing out, losing focus, waiting for an app to load. These micro-interruptions aren't catastrophic. They're just constant. And collectively, they cost hours.

Nimble is a lightweight, cross-platform hotkey daemon for Python developers that turns those interruptions into instant, keyboard-triggered actions. Press a shortcut, get your result — without leaving your current context. Workflows are Python classes, tools are modular (AI queries, popups, clipboard manipulation, TTS, user input), and the whole thing ships as a forkable template repository that developers own completely.

The timing is right. Existing hotkey automation tools are fragmented by platform and language: AutoHotkey is Windows-only with a proprietary scripting syntax; Raycast is macOS-only and closed; sxhkd is X11-only and breaking under the Wayland transition now underway on Ubuntu, Fedora, and Arch. No cross-platform, Python-native solution exists. Meanwhile, 84% of developers are actively integrating AI into their workflows — and Nimble provides the missing last mile: triggering an AI query from anywhere, with one keypress.

## The Problem

Python developers encounter small, repetitive context-switching tasks constantly: querying an AI assistant, translating selected text, cleaning clipboard content, summarizing a paragraph. The tools that exist to automate these actions fall short in consistent ways:

- **AutoHotkey** owns Windows automation but requires learning a proprietary scripting language — a non-starter for developers who already write Python
- **Raycast** is macOS-only with a closed JavaScript extension model; Linux and Windows developers are explicitly left out
- **sxhkd / xdotool** are X11-only Linux primitives that have become unreliable as Wayland replaces X11 across major distributions
- **General automation platforms** (n8n, Zapier) are cloud/server tools with no concept of a local keyboard shortcut or desktop context

The gap is simple: no tool lets a Python developer write `def run(context, tools): tools.ai.ask(context.selection)`, bind it to `Ctrl+E`, and be done — on both Linux and Windows.

## The Solution

Nimble is a background daemon that listens for global keyboard shortcuts and executes user-defined Python workflows. Each workflow is a Python class that receives a context object (selected text, clipboard content, active application name) and a set of modular tool primitives. Configuration lives in a YAML file mapping shortcuts to workflows.

**The experience:**
1. Developer forks the Nimble template repository
2. Writes a workflow, or installs one: `nimble add ctrl+e github.com/user/translator-workflow`
3. Restarts the daemon
4. Presses the shortcut from anywhere — gets an immediate result (popup, clipboard update, TTS, AI response)

**Example scenarios:**
- `Ctrl+Shift+T` — translate selected text, show result in a popup
- `Ctrl+Shift+A` — send selected text to an AI model, stream the answer
- `Ctrl+Shift+S` — summarize clipboard content and replace it with the summary

Tool primitives have intentionally simple APIs (`tools.ai.ask(text)`, `tools.popup.show(text)`). Pydantic validates workflow inputs so user-written code doesn't fail silently.

## What Makes This Different

- **Python-native**: No new language to learn. Workflows are plain Python classes — developers use the tools, debuggers, and libraries they already know.
- **Cross-platform**: Linux (pynput/evdev) and Windows (pywin32/pynput), with OS-specific adapters isolated behind a clean interface so the core stays portable.
- **Forkable, not installable**: The template repository model means developers own their setup completely — no platform account, no extension marketplace, no gatekeeping. Keystrokes never leave the local machine.
- **AI-first by design**: The AI tool module is a first-class primitive, not a plugin. Building an AI-powered hotkey takes the same effort as building a clipboard action.
- **AI-assisted workflow authoring**: The template ships with `skill-build.md` — a structured context file that gives an AI assistant (Claude, Copilot) everything it needs to scaffold new workflows from a plain English description. Building a new tool becomes a conversation, not a documentation dive.
- **Distributed without a platform**: `nimble add <shortcut> <repo-url>` pulls community workflows directly from GitHub — the distribution layer is git, which developers already trust.

## Who This Serves

**Primary — Python developers on Linux or Windows** who write scripts to automate their own work, are comfortable reading and modifying Python, and are frustrated by the lack of a hackable, cross-platform hotkey automation framework. They know what they want to build; Nimble gives them the scaffold.

**Secondary — AI-curious developers** experimenting with LLM-powered personal tools who want the shortest path from "I have an API key" to "I have a hotkey that does something useful."

## Success Criteria

As a personal OSS project, success looks like:

- **Personal utility**: Nimble reliably automates the author's own repetitive tasks day-to-day
- **Community signal**: Other developers discover, fork, and star the template repository
- **Ecosystem emergence**: Community workflows appear and spread via `nimble add` — the distribution mechanism works in practice, not just in theory
- **DX validation**: The `skill-build.md` pattern proves useful — developers report that AI assistants can scaffold new workflows effectively from it

## Scope

**In for v1:**
- Global hotkey daemon for Linux (X11) and Windows
- Core engine: context builder, workflow loader, tools registry
- Tool primitives: popup, AI query, clipboard, TTS, selector, question dialog
- Global error handler: when any workflow raises an unhandled exception, a system-level notification fires with the error summary — no silent failures
- YAML configuration: shortcut → workflow mapping
- `nimble add <shortcut> <repo-url>` CLI for community workflow installation
- Template repository structure with `skill-build.md` for AI-assisted authoring
- systemd service (Linux) and Task Scheduler integration (Windows)

**Out of scope for v1:**
- macOS support
- Wayland-native global hotkey support (X11 compatibility path for now; Wayland imposes compositor-level restrictions that require per-compositor work)
- GUI configuration editor
- Centralized workflow marketplace / discovery layer
- Sandboxing or code-signing for community workflows

**Known risks:**
- `nimble add <repo-url>` executes arbitrary Python from a remote source — users bear responsibility for vetting community workflows; no sandbox or signature verification is provided in v1
- Linux users on Wayland-only desktops will not have global hotkey support without an X11 compatibility layer (XWayland)

## Vision

If Nimble finds its community, it becomes the missing automation layer of the Python developer's desktop: a personal runtime where every repetitive action has a hotkey, every workflow is version-controlled and shareable, and every AI interaction is one keypress away. The `nimble add` ecosystem evolves organically into a decentralized catalog of developer workflows distributed through GitHub — no platform, no gatekeeping, just Python.
