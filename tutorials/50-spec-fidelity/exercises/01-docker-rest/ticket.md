# OPS-1432 — Dockerize the FX conversion function

| Field | Value |
|---|---|
| Type | Story |
| Priority | Medium |
| Reporter | billing-team |
| Sprint | 34 |
| Story points | ? |

## Description

Billing needs a small function they can call over REST to convert invoice
amounts between currencies. Should be fast and handle errors properly. Put
it in Docker so it runs anywhere. Use the usual rates. Should be secure.

## Acceptance criteria

- works
- returns the converted amount
- handles bad input

## Comments

> **billing-team:** we need this before month end, thx
