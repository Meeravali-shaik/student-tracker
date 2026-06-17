# Student Coding Journey Tracker

## Overview
A Streamlit + Supabase application that guides students through HackerRank and LeetCode practice tracks.

## Features
- Student profiles
- HackerRank Python / Java tracks
- LeetCode Python / Java tracks
- Sequential problem unlocking
- Progress tracking
- Leaderboard
- Admin dashboard (KPI cards, charts, export features) built with Flask, Bootstrap 5, Chart.js, and pandas/openpyxl for reporting.
- Submission verification workflow

## Tech Stack
- Streamlit
- Supabase (PostgreSQL)
- Python

## Database Tables
- students
- tracks
- problems
- progress
- submissions
- admins

## Project Structure
student-tracker/
├── app.py
├── pages/
├── database/
├── services/
├── utils/
└── requirements.txt

## Run Locally

pip install -r requirements.txt

streamlit run app.py

## Future Enhancements
- Auto verification
- Streaks
- Badges
- Certificates
- Analytics dashboard
