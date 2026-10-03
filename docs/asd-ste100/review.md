# Editorial review

## Scope and method

The source is the TAK console task manual and its four linked task chapters.
The bilingual data contains 166 original blocks. Each block has an unchanged
source snapshot, a Traditional Chinese revision, and an English revision.
The comparison pages retain source block order. The standalone manuals move
download credential warnings and publisher credential warnings before the
affected procedures.

The requested ASD-STE100 skill supplied the procedure, description, safety,
and reference checks. Its official controlled dictionary was not available.
The English draft has structural review coverage only, not certified vocabulary
or full ASD-STE100 conformance. The Chinese revision applies the transferable
writing principles, not English word-count or dictionary rules.

## Changes by text type

| Text type | Revision | Preserved constraints |
| --- | --- | --- |
| Procedure | Split compound steps. Name the action. Repeat a condition when it controls multiple steps. | Sequence, prerequisites, optional actions, exact commands, and UI labels. |
| Description | Use short sentences and one subject per paragraph. | Causal limits and distinctions between shared and device-specific credentials. |
| Risk statement | Put revocation, interruption, and credential exposure information before the relevant action. | Irreversibility, affected services, and recovery limits. |
| Reference | Keep explicit task anchors, figures, dates, and links. Rebase links for the new location. | Original evidence scope and device test limitations. |

The Mumble actions are alternatives, not a required sequence.
Public WebRTC control does not stop ICU publication.
A TAK group change controls alias visibility, not an already known viewer password.
An import notice does not establish a successful connection or video publication.
The CA replacement instructions retain the requirement to test old and new
certificates on 8443 after each replacement.
Reissuing a QR does not rotate a password.
Password reset requires redistributing credentials and checking the old connection.
A statement that a connection is disconnected remains a check, not a new command
to disconnect it.

## Technical correction

The original troubleshooting block lists only `takbox.local:8322` for ICU.
The revised row distinguishes default RTSP `takbox.local:8554` with SSL clear
from RTSPS `takbox.local:8322` with SSL enabled.
The constants and SSL preference construction in
[build_icu_qr.py](../../scripts/build_icu_qr.py) and the
[ICU QR reference](../mediamtx/icu-qrcode.md) support this correction.
The original block remains in the comparison data.

Statements about the original validation scope are explicitly attributed to
the source. No new service acceptance result is claimed.
The external source documents and screenshot labels remain in their original
language.

## English advisory review

The linter reports candidates rather than proven defects. No rule is disabled,
and the hard-finding baseline remains zero. The current detailed findings are in
[checks/ste.json](checks/ste.json).

| Candidate | Decision and reason |
| --- | --- |
| `are concealed` | Retain in screenshot captions. The source does not name the person who concealed identifiers. |
| `was submitted` | Retain the negative statement about screenshot evidence. Do not invent an actor or imply submission. |
| `was restored` | Retain the historical configuration statement. The actor is not supplied. |
| `is published` | Retain the CRL acceptance state in the task table. The detailed procedure names the console. |
| `is selected`, `are selected` | Retain descriptions of default UI state. They are not instructions to select additional items. |
| `are applied` | Retain the limit on what a screenshot proves about device settings. |
| `was deactivated` | Retain the historical test state without an invented actor. |
| `is disconnected` | Retain the state to check after password reset. Do not turn the check into a disconnect command. |
| `is logged` | This is the required Windows login state. It is not an instruction to start a new login. |
| `confirm` / `check` | Confirmation authorizes an operation. Checking inspects a value or result. Decoding confirmation is an acceptance result. |
| `display` / `show` | Display occurs in field names and UI labels, including Altitude Display and Coordinate Display. |
| `remove` / `delete` | Group membership removal and identity/package deletion refer to different objects and effects. |
| `verify` / `check` | TLS certificate-chain and hostname verification is a specific security operation. |
| `obtain` / `get` | The source distinguishes an operator obtaining replacement URLs from a member receiving a QR. |

## Traditional Chinese review

[glossary.json](glossary.json) records the project terms and reasons.
Certificate revocation must not become an undo operation.
The established console name remains consistent with the source.
The exact general-device UI path uses inline code, while narrative text uses
the Taiwan term for device.

The two informational tricolon findings in the certificate chapter identify
actual expiry option lists. Keep all durations. Do not change technical options
to eliminate an informational style pattern.

The gate requires zero errors and zero warnings. AI-style and translationese
detection remain enabled. No automatic text fixes or broad rule disabling are used.
Only the revised Chinese pages and the bilingual entry README are gated.
Unchanged original columns are historical source quotations.

## Verification limits

The script checks source coverage, output freshness, preserved inline identifiers,
numeric token presence, explicit task anchors, local links, Markdown table cell
counts, and English procedure sentence length. Numeric checks ignore list numbering and do not prove the
meaning of a quantity or the relationship between quantities.
The supplied STE linter checks additional structural patterns.
A fresh zhtw-mcp run writes file hashes and tool trace metadata.

These checks do not prove technical equivalence, safety, dictionary approval,
external URL availability, or live TAK/Android behavior. The editorial comparison
preserves the documented scope and limitations. Refer to the linked original
validation records for service test evidence.
