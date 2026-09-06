# Arbeitsverfassung – Orchestrierung und Alignment

**Version:** 1.0 · **Release:** ALIGN-2026-09-06-v1.0  
**Verbindlicher Fokus:** `07_RESEARCH_PROGRAM_SOT.md`  
**Zweck:** Getrennte Arbeit ohne getrennte Forschungsziele.

## 1. Rollenmodell

**Anton** bleibt Programmeigner und finaler Entscheider über Forschungsfokus, Aufwand, Canonical-/Protokolländerungen, reale Inputs, Merge und externe Einreichung/Kontaktaufnahme.

**TECH-ORCH** verantwortet technische Best-Practice-Prüfung, Forschungstauglichkeit des Apparats, Repo-/Issue-Planung, Codex-Tickets, Integration und technische Evidenz. Er produziert keine konkurrierende Dissertationsrichtung.

**SCI-ORCH** verantwortet wissenschaftliche Kohärenz, kritische Gap-Prüfung, Studien-/Claim-Plan, Artefaktaufträge, Quellenregister und Schreibqualität. Er arbeitet selbst analytisch und reviewt die Ergebnisse; er ist nicht bloß ein Promptverteiler.

**Fachchats** bearbeiten jeweils genau einen erteilten Artefaktauftrag oder eine begrenzte technische Reviewfrage. Sie dürfen den Scope nicht selbst erweitern und keine weiteren Chats beauftragen. Zusätzlicher Bedarf geht an ihren Orchestrator.

**Codex** implementiert genau ein freigegebenes GitHub-Leaf-Issue gemäß `AGENTS.md`. Der technische Orchestrator koordiniert diese Arbeit; kein wissenschaftlicher Fachchat vergibt parallel Implementierungstickets.

**Reviewer** prüft einen eingefrorenen Kandidaten ohne ihn gleichzeitig umfassend umzuschreiben. Unabhängiger Review-Chat reduziert Kontextkopplung, beweist aber keine statistische Unabhängigkeit seiner Urteile.

## 2. Zuständigkeiten und Freigaben

| Gegenstand | Verantwortlich | Obligatorische Rückkopplung | Endentscheidung |
| --- | --- | --- | --- |
| Forschungsfokus / Fragenänderung | SCI-ORCH | TECH-ORCH für Machbarkeit | Anton |
| Architektur / neue Modellklasse / große Dependency | TECH-ORCH | SCI-ORCH bei Mess-/Treatmentfolgen | Anton bei Scope-/Grenzänderung |
| Gewöhnliches Leaf-Issue | TECH-ORCH / Codex | Review + CI | Anton merged |
| Literatur- und Gap-Urteile | SCI-ORCH | Fachreview, Primärquelle | SCI-ORCH fachlich; Anton bei Richtungswechsel |
| Endpunkte / Randomisierung / Protokoll | SCI-ORCH | TECH-ORCH für Messbarkeit/Logging | Anton friert Studienfassung ein |
| Technical-Report-Claims | SCI-ORCH als Herausgeber | TECH-ORCH bestätigt technische Belege | Anton vor externer Nutzung |
| Exposé / Papers / Dissertation | SCI-ORCH | Fachchat + Review; Technik bei Implementierungsclaims | Anton vor Kontakt/Einreichung |
| Kanonische Regeln / Run-Modi / Phase-Gates | Beide im Change Request | Auswirkungen explizit prüfen | Anton |
| Live-Spiel / reale Inputs / Netzfreigaben | TECH-ORCH prüft Voraussetzungen | Geltendes Protokoll | Explizite Autorisierung durch Anton |
| Upload- und Repository-Synchronisation | TECH-ORCH stellt Release bereit | SCI-ORCH bestätigt gelesene Version | Anton aktiviert Lesekopie |

Fachliche Freigabe ist nicht User-Merge, nicht Betreuungszusage und nicht Publikationsannahme. Status müssen getrennt bleiben.

## 3. Zwei parallele Starts, ein gemeinsames Startgate

TECH-ORCH beginnt mit **T0: technischem Alignment-Review**. SCI-ORCH beginnt mit **S0: wissenschaftlichem Alignment-Review**. Beide verwenden dieselbe SOT-Version.

T0 ermittelt den kleinsten passenden technischen Weg; S0 ermittelt den ersten prüfbaren Forschungsfall und die dafür wirklich nötigen Nachweise. Die Ergebnisse werden über Anton gegenseitig übergeben. Das Startgate ist erreicht, wenn

- beide denselben Fokus A/B und dieselben Nichtziele bestätigen;
- Änderungen am bestehenden Pilot ausdrücklich benannt sind;
- die minimal nötige Datenspur und die offenen methodischen Anforderungen sichtbar sind;
- keine ungeklärte Grenzverletzung die nächste Änderung betrifft;
- Anton den nächsten begrenzten Arbeitsumfang freigegeben hat.

Nicht erforderlich sind ein vollständiges Literaturkompendium, eine perfekte End-to-End-Architektur oder eine endgültige Dissertationsthese. Ein fehlender Neuheitsbeleg blockiert einen Gap-Claim, nicht automatisch jede zulässige Dry-run-Integration. Konflikte blockieren nur die davon betroffene Arbeit.

## 4. Auftrag statt freier Themenwanderung

Jeder Fachchat erhält einen vollständigen Auftrag mit

`Auftrags-ID · Parent-Orchestrator · genau einem Zielartefakt · SOT-Version · Quellenständen · Zweck/Audience · Scope/Non-goals · erlaubten Operationen · erwarteten Dateien · Akzeptanzkriterien · Claim-Grenzen · Rückgabeformat`.

Eine Gliederung oder Quellenliste ist kein Ersatz für einen präzisen Auftrag. Ein Fachchat beginnt damit, seine gelesenen Quellen, das Artefakt und die Grenzen kurz zu nennen. Er arbeitet dann am Auftrag, ohne erneut sämtliche Forschungsrichtungen zu erkunden.

Der Orchestrator liefert Anton bei Delegation genau: empfohlenen Chatnamen, fertigen Startprompt, benötigte Quellen/Anhänge, erwarteten Output und die Stelle, an die das Ergebnis zurückzugeben ist. Anton eröffnet den Chat und überträgt dessen Ergebnis. Kein Chat behauptet, andere Chats eigenständig erstellt, dauerhaft überwacht oder im Hintergrund beauftragt zu haben.

## 5. Keine stillschweigende Kommunikation zwischen Chats

Gemeinsamer Projektkontext hilft beim Auffinden, ersetzt aber keine versionierte Übergabe. Es wird **nicht** vorausgesetzt, dass ein Chat den vollständigen aktuellen Verlauf eines anderen kennt.

Eine Übergabe enthält: Auftrags-ID, Referenzversionen, Ergebnisstatus, tatsächliche Dateien, was geändert wurde, was nicht geprüft wurde, Belege, offene Konflikte und nächsten empfohlenen Schritt. Der Empfänger bestätigt die Version und nennt Auswirkungen auf seinen Scope.

Nach einer grenzüberschreitenden Entscheidung sendet der zuständige Orchestrator eine kurze **Alignment-Delta** an den anderen: `Entscheidung / Referenz / betroffene Claims, Tests, Dateien / Handlungsbedarf / User-Freigabe`. „Im anderen Chat besprochen“ ist ohne dieses Delta kein dauerhafter Beleg.

## 6. Arbeitsbegrenzung und Datei-Ownership

Zu Beginn höchstens ein aktives technisches Leaf-Issue und höchstens zwei klar voneinander getrennte wissenschaftliche Artefaktaufträge. Kein paralleles Bearbeiten derselben Quelldatei oder desselben primären Studienkontrasts.

SCI-ORCH führt das aktive Artefaktregister und integriert Schreibänderungen. TECH-ORCH führt die technische Lieferkette und die Registrierung gemeinsamer Quellen im Repository. Wissenschaftliche Inhalte werden von TECH-ORCH bei der Registrierung nicht redaktionell verändert; fachliche Rückfragen gehen zurück.

Ein Fachchat liefert eine neue versionierte Kandidatenfassung plus Changelog. Er überschreibt kein anderes Artefakt als Nebenwirkung. PDF/DOCX/LaTeX sind Renderings beziehungsweise jeweilige Manuskriptquellen nach Auftrag; es darf nicht unbemerkt mehrere unabhängige Textmaster geben.

## 7. Versions- und Änderungsregeln

Format des gemeinsamen Release: `ALIGN-YYYY-MM-DD-vMAJOR.MINOR`. Version in allen Rollen-/Auftragsköpfen festhalten.

- Kleine Klarstellung ohne Scope-/Methodenänderung: Minor-Revision mit Changelog und Benachrichtigung.
- Fokuswechsel, Primärendpunkt, Informationszugang, Run-Modus, Kontrollautorität oder Studienpopulation: expliziter Change Request und Nutzerentscheid.
- Typografische Korrekturen in einem Fachartefakt: innerhalb des Auftrags zulässig; keine Claim-Änderung verstecken.

Ein Change Request nennt Ist-Zustand, Änderung, Begründung, Quellen, Alternativen, Auswirkungen auf frühere Daten/Artefakte, Kosten und Rollback. Zwei Orchestratoren können einander widersprechen; Anton entscheidet nach benannten Optionen. Ein Orchestrator darf eine wissenschaftliche Erkenntnis als widerlegt melden, aber nicht die Hauptfrage unbemerkt ersetzen.

Vorgeschlagene Status: `DRAFT → IN_REVIEW → DOMAIN_ACCEPTED → USER_APPROVED → PUBLISHED`. Dazu `BLOCKED` und `SUPERSEDED`. Ein hochgeladenes Dateiartefakt ist nicht automatisch USER_APPROVED; ein Draft PR nicht MERGED; ein bestandenes Unit-Testset kein LIVE_VALIDATED.

## 8. Technische Lieferung und Milestones

Der aktuelle Repo-Workflow bleibt maßgeblich:

`Ready GitHub Issue → codex/<issue-number>-<slug> → fokussierte lokale Tests/Static Checks → Draft PR → volle GitHub-CI → Review → expliziter User-Merge`.

Kein direktes Arbeiten auf main, kein selbsttätiger Merge und kein Done allein wegen eines erzeugten Drafts. Keine neuen historischen M-XXX-Routinen nach dem dokumentierten Cutover. Operative Arbeit gehört in GitHub Issues/Project/Milestones, nicht in ständig neue kanonische Fortschrittstabellen.

T0 darf eine Roadmap-Mappingtabelle vorschlagen: `behalten / umpriorisieren / ergänzen / später / freigabepflichtig`. Bestehende Issues und Exit-Gates werden nicht gelöscht, um einen Plan passend erscheinen zu lassen. Kanonische Roadmapänderungen brauchen gesonderte Freigabe. Ordinary full-suite runs richten sich nach `AGENTS.md`; keine neuen pauschalen Testpflichten aus einem Schreibchat.

## 9. Wissenschaftliche Behauptungen und Recherche

Jeder maßgebliche Claim gehört zu einer Klasse: `Literaturbefund`, `Projektentscheidung`, `Implementierung`, `eigene empirische Evidenz`, `Hypothese` oder `offen`. Die Belege müssen zur Klasse passen.

Ein Literaturlead wird nicht durch Wiederholung zur geprüften Quelle. Version, Datum, Publikationsstatus, geprüfte Abschnitte und konkrete Unterstützung werden dokumentiert. Autoren-Limitationen und eigene Ableitungen werden getrennt. Fremde Claims über „optimal“, „erstmals“ oder „notwendig“ werden nicht ungeprüft übernommen.

Eine neue Paperidee erhält kein automatisches Implementierungsbudget. Umgekehrt darf eine technisch elegante Komponente nicht nachträglich zur angeblich ursprünglichen Forschungslücke erklärt werden.

## 10. Mindestabschluss jeder Arbeitseinheit

Jeder Orchestrator oder Fachchat liefert einen kurzen Abschlussblock:

1. Erfüllter Auftrag und Status.
2. Gelesene SOT-/Quellen-/Commitversionen.
3. Konkrete Ergebnisse und Dateien mit bestätigten Pfaden.
4. Belege und tatsächlich ausgeführte Checks.
5. Nicht geprüft / offen / mögliche Widersprüche.
6. Änderungen, die eine andere Rolle betreffen.
7. Genau ein nächster sinnvoller Auftrag oder eine gezielte Entscheidung.

Keine Hintergrundversprechen. Keine behauptete Weitergabe ohne tatsächliches Übergabepaket. Neue Chats erhalten den aktuellen Auftrag und die aktuellen Dateien, nicht nur den Hinweis „lies den alten Chat“.

## 11. Qualitätskontrolle gegen Drift

Warnsignale: A/B verschwindet hinter neuem Body-/Benchmarkbau; „corrupted memory“ wird wieder Hauptfokus; alle Modellunterschiede heißen Persönlichkeit; synthetische Ergebniszahlen wandern als Daten ins Exposé; zusätzliche Evaluatorinformation wird Agenteninput; Cross-Run-Synthese wird aus einem einzigen RAG-Beispiel behauptet; ein neuer Modellname ersetzt die Forschungsfrage.

Bei einem Warnsignal: Claim/Änderung isolieren, Ausgangsquelle nennen, Scope-Abweichung erklären und entweder innerhalb des Auftrags korrigieren oder Change Request stellen. Kein Neustart der gesamten Forschungssuche als Standardreaktion.
