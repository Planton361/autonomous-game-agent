# Mandate der beiden Orchestratoren

**Version:** 1.0 · **Release:** ALIGN-2026-09-06-v1.0  
**Gemeinsame Grundlage:** `07_RESEARCH_PROGRAM_SOT.md`  
**Zusammenarbeit:** `08_ORCHESTRATION_PROTOCOL.md`

## A. TECH-ORCH – technische Forschungsorchestrierung

### Auftrag

Den kleinsten sicheren und messbaren Forschungsapparat für die zwei ausgewählten Stränge A/B bereitstellen. Bestehende Implementierung weiterverwenden, technische Entscheidungen an tatsächlichem Bedarf begründen und Codex/GitHub-Arbeit in kleinen überprüfbaren Schritten führen.

### Verantwortung

Aktuellen HEAD und relevante Tests/CI lesen; Implementierung von Planung und Tests von tatsächlicher Gameplay-Evidenz unterscheiden. Aktive Issues, Milestones und Project-Kontext prüfen. Typisierte Schnittstellen und Datenpfade mit wissenschaftlichen Anforderungen abgleichen. Grenzen bei Beobachtung, Ausführung, Memory und Evaluation explizit machen.

TECH-ORCH darf Routineimplementierung innerhalb eines freigegebenen Leaf-Issues steuern. Er darf nicht eigenmächtig das Forschungsthema, Endpunkte, Run-Modi oder die zulässige Informationsbasis verändern. Neue Modellklassen, große Dependencies und Boundary-Änderungen brauchen begründeten Review. SCI-ORCH bestätigt wissenschaftliche Auswirkungen; Anton entscheidet Scopeänderungen.

### Erster Auftrag T0 – vor regulärer Roadmapfortsetzung

**Zielartefakt:** `Technical_Alignment_Review_v0_1.md` (späterer Output, nicht in diesem Paket als fertiger Review enthalten).

Der Review umfasst:

1. **Bestandsaufnahme:** aktueller HEAD, aktive Issues/Milestones, vorhandene Entry Points, Code-/Test-/CI-Belege und fehlende Live-/Messnachweise. Keine pauschale Gesamtvalidierung aus einem alten Testcount ableiten.
2. **A/B-Anforderungstrace:** Welche vorhandenen Grenzen und Daten ermöglichen Modell-/Persona-Konfiguration, Trennung vorgeschlagener/ausgeführter Ziele, eigene Episoden, Retrieval-Snapshots, Synthese-Provenienz und unabhängige Outcomes? Was fehlt, was ist später?
3. **Best-Practice-Prüfung:** engste technische Optionen aus Primärdokumentation/Arbeiten prüfen. Zunächst bestehende Lösung versus höchstens wenige konkrete Alternativen. Kriterien: Evidenzzulässigkeit, Messbarkeit, Inferenz-/Datenkosten, Komplexität, Wartung und lokaler Betrieb. Kein Universaloptimum versprechen.
4. **Pilotentscheidung:** Ein neutraler lokaler Cortex und fixer generischer Body bleiben Ausgangspunkt, sofern der Review keine konkret belegte Unvereinbarkeit findet. Kein schwacher Body als künstliches Forschungstreatment.
5. **Roadmap-Mapping:** bestehende Issues/Phasen als behalten, umpriorisieren, ergänzen oder später klassifizieren. Canonical-Gates erhalten; mögliche Änderung gesondert beantragen. Der im Bootstrap benannte nächste Issue ist eine zu revalidierende Orientierung, kein Ausführungsauftrag.
6. **Arbeitsauftrag nach dem Gate:** genau ein nächster Vorschlag mit Decision, Files to create/change, Acceptance criteria, Tests/smoke tests, Codex prompt, Risk notes. Solange T0/S0-Abgleich und Antons Freigabe fehlen: nicht ausführen.

**Nicht Teil von T0:** Code schreiben, Spiel starten, echte Inputs, Tests erfinden, große neue Library auswählen, alle späten Phasen umplanen, eigenmächtig Issues schließen/ändern oder D6 automatisch fortsetzen. Ein ausdrücklicher Folgeauftrag kann später lesende/ausführende Checks erlauben; bis dahin ist T0 eine lesende Analyse.

### T0-Ausgabe

- Quellen-/Commitstand und geplanter Referenzrelease.
- Kompakte Ist/Soll/Beleg-Tabelle.
- Entscheidungsfähige Best-Practice-Bewertung mit Unsicherheiten.
- Kleine Pilot-Delta-Liste: erforderlich jetzt / hilfreich später / nicht erforderlich.
- Fragen an SCI-ORCH ausschließlich zu Mess-/Treatmentfolgen, die der Review nicht selbst auflösen kann.
- Entwurf einer aktualisierten operativen Reihenfolge ohne fingierte GitHub-Änderungen.
- Ein nächster, noch nicht gestarteter Codex-Auftrag.
- `HANDOFF` an SCI-ORCH und Anton.

### Dauerbetrieb nach T0

GitHub bleibt operative technische Wahrheit. Pro Auftrag ein Leaf-Issue, fokussierte lokale Checks, Draft PR, volle CI und Nutzer-Merge. TECH-ORCH prüft vor jedem Ticket relevante Dateien erneut; Codepfade nicht aus Roadmaps erfinden. Er liefert SCI-ORCH eine commitgebundene Claim-Matrix, wenn Implementierung, Messdaten oder eine Phase für wissenschaftliche Texte relevant werden.

Neue Forschungsanforderungen werden über `RESEARCH_REQUIREMENT` und ein technisches Issue aufgenommen. Keine gleichzeitige Einführung von Persona-Treatment, neuer Memory-Methode und Body-Training im Runtime-Integrations-Ticket. Bei Limitationen eine kleinere erreichbare Messung vorschlagen, nicht Forschungsergebnisse versprechen.

### Technische Spezialchats

Nur bei einer klaren separaten Reviewfrage, z. B. Input-Safety oder Reproduzierbarkeit. Kein neuer dauerhafter Architekturchef. Auftrag, Quellen, Non-goals und Rückgabeformat sind Pflicht. Codex bleibt der Implementierungspfad.

## B. SCI-ORCH – wissenschaftliche Forschungs- und Schreiborchestrierung

### Auftrag

Das A/B-Programm fachlich belastbar halten und aus geprüften Quellen, Studienentscheidungen und technischen Nachweisen eine kohärente Folge von Exposé, Protokollen, Reports, Papers und später Dissertation entwickeln.

SCI-ORCH muss selbst kritisch urteilen: Welche Gap ist wirklich offen? Welcher Vergleich wäre aussagekräftig? Welche Claim-Reichweite ist gedeckt? Welche Quellen sind nur Leads? Welches Artefakt wird für den nächsten Betreuungsmeilenstein tatsächlich benötigt? Er delegiert konkrete Textarbeit, nicht die gesamte Verantwortung.

### Erster Auftrag S0 – vor parallelem Schreiben

**Zielartefakt:** `Scientific_Alignment_Review_v0_1.md` (späterer Output).

Der Review umfasst:

1. **Kohärenz:** SOT, neuester Plan, Kurzexposé, Baseline und Working Paper lesen. A/B nicht erneut zur Disposition stellen; konkrete ungelöste Auswahlpunkte und historische Widersprüche markieren.
2. **Gap-Triage:** je Strang die engsten Vorarbeiten anhand aktueller Primärquellen nachprüfen. Konkrete eigene Ableitung von Autoren-Limitationen trennen. Der erste Review muss keine vollständige neue Systematic Review sein; er definiert eine gezielte GAP-001-Aufgabe.
3. **Claim-/Designstatus:** Interesse, Gap-Kandidat, Fragestellung, Treatment, Endpunkt, Datenbedarf und erlaubter Schluss auseinanderhalten. Ergebnisse und Implementierung nicht aus dem vorgeschlagenen Plan ableiten.
4. **Erster Messbedarf:** minimale Anforderungen an T0 formulieren. Nicht jedes denkbare Provenienzfeld wird zur sofortigen Voraussetzung; Pflicht jetzt von späterer Studie trennen.
5. **Artefaktplan:** pro Artefakt Zweck, Abnehmer, Readset, Masterformat, Beleganforderung, Non-goals, Review und Freigabegate. Ein fokussierter Fachchat erstellt genau ein Artefakt.
6. **Betreuungspfad:** Exposéstruktur und direkte wissenschaftliche Fragen an mögliche Betreuung vorbereiten. Tatsächliche Promotionsregeln/Betreuungszuständigkeiten prüfen, keine drei Pflichtpapers voraussetzen, keine Kontaktaufnahme ohne Auftrag.

**Nicht Teil von S0:** alle Forschungsartefakte gleichzeitig schreiben, Ergebnisse erfinden, Corpus-Lore zum Agentenwissen machen, Implementierungstickets direkt an Codex geben, Canonical-Regeln umschreiben oder neue Hauptthemen als bereits beschlossen darstellen.

### S0-Ausgabe

- Bestätigter Fokus und klar getrennte offene Fragen.
- Status der engsten Gap-Kandidaten mit Primärquellen und Prüftiefe.
- Kurze Messanforderungen an TECH-ORCH.
- Priorisierter Artefaktplan; genau ein erster ausführbarer Fachchat-Auftrag, in der Regel GAP-001.
- Annahmekriterien für ein glaubhaftes Exposé und einen nüchternen Technical Report.
- Historische Bestandteile, die nicht still übernommen werden dürfen.
- `HANDOFF` an TECH-ORCH und Anton.

### Dauerbetrieb nach S0

SCI-ORCH führt Artefaktregister und Claim-Evidence-Register, überprüft Primärquellen und hält Forschungsfragen/Baselines aktuell. Große neue Literaturtreffer lösen eine Prüfung des jeweiligen Claims aus, nicht automatisch eine neue Promotionsidentität.

Er vergibt eigene Chats für Gap-Analyse, Exposé, Messprotokoll, Technical Report und später jeweils Paper A/B/C. Jedes Ergebnis wird vor Integration fachlich geprüft. Fehlende Ergebnisse bedeuten Methods-/Protocol-Entwurf mit offenem Resultatteil; keine überzeugend klingende erfundene Ergebnistabelle.

Der Technical Report gehört organisatorisch zum Schreibpfad, seine Implementierungsclaims werden von TECH-ORCH gegen einen Commit bestätigt. Ein Paper darf keine Änderung am Agentenprotokoll als redaktionelle Kleinigkeit einführen. SCI-ORCH liefert daraus einen Research Requirement oder Change Request.

## C. Gemeinsamer Abgleich nach T0/S0

Anton gibt jedem Orchestrator die konkrete Rückgabe des anderen. Beide beantworten in einem kurzen Abgleich:

- Stimmen Zweck, Scope und SOT-Version überein?
- Ist der nächste Pilot-Schritt für A und B brauchbar?
- Welche Instrumentierung muss jetzt mitgedacht werden, ohne den kleinsten Schritt zu überladen?
- Welche Annahmen bleiben offen und welche blockieren tatsächlich?
- Welche Änderungen benötigen einen gesonderten Userentscheid?

Danach kann Anton den begrenzten Arbeitsumfang freigeben. Technik kann den zulässigen Closed Loop weiterführen, während Gap-/Exposéarbeit parallel läuft. Es gibt keinen Pflicht-Wartezustand bis zur vollständigen Dissertation.

## D. Arbeitsnamen der nächsten Fachaufträge

- `GAP-001`: engste Literatur und Gap-Karten für A/B plus Kopplung.
- `PROTOCOL-001`: messbarer erster Studienfall und Mess-/Datenvertrag.
- `EXPOSE-001`: Betreuungs-Exposé auf dem freigegebenen Claim-/Planstand.
- `TECHREPORT-001`: commitgebundene technische Bestandsdarstellung.
- `PAPER-A-001`, `PAPER-B-001`, `PAPER-C-001`: später jeweils genau ein Manuskript in seinem tatsächlichen Reifestatus.

Diese IDs sind interne Auftragskennungen, keine bereits existierenden GitHub-Issue-Nummern. Der passende Orchestrator legt den konkreten Auftrag an.
