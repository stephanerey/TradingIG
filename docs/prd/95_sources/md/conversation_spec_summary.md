# Conversation-derived Specification Summary

**Last updated:** 2026-05-07

## Core user workflow
The user manually compares US Tech 100, France 40, Germany 40, and Spot Gold on IG, selects a Barrier/Option product, chooses quantity/stop/limit/KO, opens a small trade, then monitors the position and manually moves the stop to reduce risk or secure gains.

## Product requirements extracted from discussion
- The application must connect first to IG APIs.
- The user must be able to configure IG credentials in a settings screen.
- The application must list/select available Barrier/Option products, not assume a single fixed EPIC.
- The chart must visually resemble IG's candle chart and overlays.
- The app must support software pending orders because delayed orders are not always available for Barriers/Options in the user's current workflow.
- The app must monitor open trades and recommend/update stop moves to break-even and then trailing/secured levels.
- The app must include market context from macro/geopolitical news, e.g. Fed announcements, geopolitical tension, oil/dollar/yields.
- The app must journal trades and analyze performance.

## Safety principles
- One good trade is better than several average trades.
- No averaging down.
- No widening stops.
- Avoid stacking correlated positions.
- The app must be able to say no trade.
- Size must remain linked to capital and max accepted risk.


## Added on 2026-05-07 — Global Market Context Ribbon
The user requested a control/status ribbon below the menu bar that summarizes global market analysis with red/yellow/green indicators. The ribbon should include macro/news context such as Fed/FOMC, scheduled releases, rates/yields, USD, oil, volatility, geopolitical risk, gold context, and data-health status. It must remain visible in the trading workspace and feed scanner, ticket builder, software pending order validation, and journaling.

The user also requested that relevant screenshots be embedded in the PRD ZIP to clarify IG-like chart/ticket/position workflows.
