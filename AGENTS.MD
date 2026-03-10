# AGENTS.md

## Project Overview

This repository contains a **Telegram Mini App** and **Telegram/VK bot** for collaborative schedule management with integration to **Google Calendar** and **Yandex Calendar**.

The main goal of the project is to allow groups of users to **collectively manage events, availability and attendance** through a Telegram Mini App interface.

The system consists of:

- Telegram Bot (entry point)
- Telegram Mini App (UI)
- Backend API
- Integration with external calendar APIs
- Notification and statistics system

Mini App runs inside Telegram clients using the **Telegram Web Apps SDK** and communicates with the bot and backend services.

---

# Core Features

## 1. Calendar Integration

External APIs used:

- Google Calendar API
- Yandex Calendar API

Capabilities:

- create events
- update events
- delete events
- sync events between users
- receive event metadata

---

## 2. Event Management

The **Main User (Owner / Admin)** can:

- create events
- edit events
- delete events
- assign participants
- send event notifications

Each event includes:

- title
- description
- start time
- end time
- participants
- attendance status

When an event is edited or deleted, **all participants receive a notification**.

---

## 3. Voting for Event Time

The system allows the event creator to create a **poll for time selection**.

Flow:

1. Admin creates event proposal
2. Multiple date/time options are provided
3. Participants vote
4. System determines the option with the most votes
5. Event is created automatically in the calendar

---

## 4. Notifications

Users receive reminders:

- before event start
- when event is changed
- when event is cancelled

Notification channels:

- Telegram bot messages
- optional push notifications via Mini App

---

## 5. Attendance Tracking

After an event:

Admin can mark users as:

- present
- absent

This data is used for statistics.

---

## 6. Statistics

The system generates reports such as:

- number of attended events
- attendance percentage
- participation history

Example report:

User:
- attended: 8 events
- missed: 2 events
- attendance rate: 80%

---

# Architecture

## Components

### 1. Telegram Bot

Responsibilities:

- authentication
- launching Mini App
- sending notifications
- receiving WebApp data

Communication:

Mini App → bot using:

Telegram.WebApp.sendData()

---

### 2. Telegram Mini App

Mini App is a **web application embedded in Telegram**.

Requirements:

- responsive UI
- mobile-first design
- support Telegram themes

Technologies:

Recommended stack:

- React 
- TypeScript
- Telegram Web Apps SDK

Capabilities:

- display calendar events
- manage participants
- voting interface
- statistics dashboard

---

### 3. Backend API

Responsibilities:

- business logic
- calendar API integration
- statistics generation
- notification scheduling

Possible stack:

- Python (FastAPI / aiogram)
- Node.js (NestJS / Express)


Main tables:

- users
- events
- participants
- votes
- attendance

---

# Repository Structure

Example structure:
****