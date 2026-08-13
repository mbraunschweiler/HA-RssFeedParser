# Umsetzungsplan: Home-Assistant-RSS-Integration für HACS

## 1. Zielbild

Es entsteht eine benutzerdefinierte Home-Assistant-Integration, die über HACS installiert werden kann und vollständig über die Home-Assistant-Oberfläche konfigurierbar ist.

Die Integration soll:

- beliebig viele RSS- und Atom-Feeds abrufen,
- neue Beiträge zuverlässig erkennen,
- Beiträge anhand konfigurierbarer Regeln filtern,
- passende neue Beiträge an eine oder mehrere `notify`-Entitäten senden,
- pro Feed einen übersichtlichen Status in Home Assistant bereitstellen,
- nach Neustarts keine bereits verarbeiteten Beiträge erneut versenden.

In der Home-Assistant-Terminologie handelt es sich um eine **Custom Integration**, nicht um ein Dashboard-Plugin. HACS kann diese Integration installieren und aktualisieren.

## 2. Empfohlene Architektur

### Ein Konfigurationseintrag pro Feed

Jeder Feed wird als eigener Home-Assistant-Konfigurationseintrag angelegt. Mehrere Feeds entstehen, indem die Integration mehrfach über **Einstellungen > Geräte & Dienste > Integration hinzufügen** hinzugefügt wird.

Vorteile:

- unterstützt 1 bis n Feeds ohne feste Obergrenze,
- jeder Feed kann unabhängig geändert, deaktiviert oder gelöscht werden,
- Fehler in einem Feed beeinflussen die anderen Feeds nicht,
- Polling-Intervall, Filter und Benachrichtigungsziele können pro Feed abweichen,
- die Lösung bleibt mit den üblichen Home-Assistant-Konfigurationsabläufen kompatibel.

### Laufzeitkomponenten

- `ConfigFlow`: legt einen Feed über die UI an und prüft URL sowie Erreichbarkeit.
- `ReconfigureFlow` beziehungsweise `OptionsFlowWithReload`: ändert alle Einstellungen später über die UI.
- `DataUpdateCoordinator`: plant Abrufe, behandelt Verfügbarkeit und aktualisiert Entitäten.
- Feed-Client: lädt Feeds asynchron und nutzt nach Möglichkeit `ETag` und `Last-Modified`.
- Parser: verarbeitet RSS 2.0 und Atom und normalisiert die unterschiedlichen Felder.
- Filter-Pipeline: entscheidet für jeden neuen Beitrag, ob er akzeptiert wird.
- Eintragsspeicher: merkt sich stabile Artikel-IDs über Home-Assistant-Neustarts hinweg.
- Notification-Dispatcher: versendet akzeptierte Beiträge über `notify.send_message`.
- Sensor-/Event-Ausgabe: zeigt den letzten akzeptierten Beitrag und meldet neue Beiträge für Automationen.

## 3. Vorgeschlagene Projektstruktur

```text
RssParser/
├── custom_components/
│   └── rss_parser/
│       ├── __init__.py
│       ├── manifest.json
│       ├── const.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── feed_client.py
│       ├── models.py
│       ├── parser.py
│       ├── filters.py
│       ├── notifications.py
│       ├── sensor.py
│       ├── diagnostics.py
│       ├── strings.json
│       └── translations/
│           ├── de.json
│           └── en.json
├── tests/
├── .github/workflows/
│   ├── validate.yml
│   └── tests.yml
├── hacs.json
├── README.md
├── LICENSE
└── plan.md
```

Falls Home Assistant für die gewählte Ereignis-Ausgabe eine eigene Plattformdatei verlangt, kommt zusätzlich `event.py` hinzu.

## 4. Datenmodell

Jeder normalisierte Beitrag sollte mindestens enthalten:

- stabile ID aus `id` oder `guid`, ersatzweise ein Hash aus Link, Titel und Veröffentlichungsdatum,
- Titel,
- Link,
- Zusammenfassung beziehungsweise Inhalt als bereinigter Text,
- Autor,
- Kategorien/Tags,
- Veröffentlichungsdatum,
- Abrufzeitpunkt,
- Feed-ID und Feed-Name.

Die Normalisierung hält Parser-, Filter-, Sensor- und Benachrichtigungslogik voneinander getrennt.

## 5. UI-Konfiguration

### Assistent zum Hinzufügen eines Feeds

Pflichtfelder:

- Anzeigename,
- Feed-URL (`http` oder `https`).

Optionale Einstellungen:

- Abrufintervall, mit einem sicheren Mindestwert,
- Zeitüberschreitung,
- Verhalten beim ersten Abruf: vorhandene Beiträge nur merken oder auch versenden,
- maximale Anzahl neu verarbeiteter Beiträge pro Abruf.

Vor dem Speichern wird der Feed einmal abgerufen und geparst. Verständliche UI-Fehler sind unter anderem `cannot_connect`, `invalid_url`, `invalid_feed`, `timeout` und `unknown`.

### Filtereinstellungen pro Feed

Für die erste Version wird eine klar definierte, gut testbare Filter-Pipeline empfohlen:

- zu prüfende Felder: Titel, Zusammenfassung, Autor, Link und Kategorien,
- Einschlussbegriffe: mindestens ein Begriff muss vorkommen; leer bedeutet keine Einschränkung,
- Ausschlussbegriffe: ein Treffer verwirft den Beitrag,
- wahlweise Gross-/Kleinschreibung beachten,
- wahlweise reguläre Ausdrücke verwenden,
- optional maximales Alter eines Beitrags,
- optional Kategorien einschliessen oder ausschliessen.

Reihenfolge:

1. Eintrag normalisieren.
2. Bereits bekannte Einträge entfernen.
3. Altersfilter anwenden.
4. Ausschlussregeln anwenden.
5. Einschlussregeln anwenden.
6. Akzeptierten Eintrag speichern, Entitäten aktualisieren und Benachrichtigung auslösen.

Reguläre Ausdrücke werden bereits im UI-Dialog validiert. Ein fehlerhafter Ausdruck darf nicht erst beim späteren Feed-Abruf auffallen.

### Benachrichtigungseinstellungen pro Feed

- Benachrichtigungen ein-/ausschalten,
- eine oder mehrere `notify`-Entitäten über einen Entity-Selector auswählen,
- Versandmodus: einzeln pro Beitrag oder gesammelt pro Abruf,
- konfigurierbarer Nachrichtentitel,
- konfigurierbares Nachrichtenformat mit dokumentierten Platzhaltern wie `{title}`, `{link}`, `{summary}`, `{author}` und `{feed_name}`,
- optionale Begrenzung der Zusammenfassungslänge.

Für die erste Version wird die aktuelle Home-Assistant-Aktion `notify.send_message` verwendet. Legacy-Aktionen wie `notify.mobile_app_xyz`, die keine `notify`-Entität anbieten, können später über einen optionalen Action-Selector ergänzt werden, falls dies in realen Installationen noch benötigt wird.

## 6. Verhalten und Zuverlässigkeit

### Erkennung neuer Beiträge

- Die letzten bekannten Artikel-IDs werden mit `homeassistant.helpers.storage.Store` persistent gespeichert.
- Der Speicher wird pro Feed begrenzt, beispielsweise auf die letzten 500 IDs oder 30 Tage.
- Beim ersten Abruf ist die sichere Voreinstellung: vorhandene Beiträge als bekannt markieren, aber nicht versenden.
- Erst nach erfolgreicher Verarbeitung wird eine ID als erledigt gespeichert.
- Die Reihenfolge mehrerer neuer Artikel wird eindeutig festgelegt, vorzugsweise alt nach neu.

### Fehlerbehandlung

- Netzwerk-, HTTP- und Parserfehler dürfen Home Assistant nicht blockieren.
- Temporäre Fehler führen zu `UpdateFailed` und werden beim nächsten Intervall erneut versucht.
- Ein defekter Feed beeinflusst keine anderen Konfigurationseinträge.
- Fehlermeldungen enthalten keine URL-Zugangsdaten oder vollständigen Feed-Inhalte.
- Ungültige einzelne Artikel werden übersprungen und protokolliert, ohne den ganzen Feed zu verwerfen.
- Bei teilweise fehlgeschlagenen Benachrichtigungen wird nachvollziehbar protokolliert, welches Ziel betroffen war; ein Ziel blockiert nicht alle anderen Ziele.

### Netz- und Ressourcenverhalten

- Home Assistants gemeinsame `aiohttp`-Session verwenden.
- Bedingte HTTP-Anfragen mit `ETag` und `If-Modified-Since` unterstützen.
- Antwortgrösse und Zeitüberschreitung begrenzen.
- Feed-Parsing, falls die Bibliothek blockierend arbeitet, über Home Assistants Executor ausführen.
- Keine dauerhaft wachsenden Sensorattribute oder Speicherdateien erzeugen.

## 7. Home-Assistant-Ausgabe

Pro Feed wird mindestens ein Sensor empfohlen:

- Zustand: Veröffentlichungszeitpunkt oder ID des letzten akzeptierten Beitrags,
- Attribute: Titel, Link, Autor, Zusammenfassung, Kategorien und Feed-Name,
- Verfügbarkeit: abhängig vom letzten erfolgreichen Feed-Abruf.

Zusätzlich sollte jeder akzeptierte Beitrag ein Integrationsereignis auslösen. Dadurch kann der Benutzer eigene Automationen bauen, auch wenn der direkte Benachrichtigungsversand deaktiviert ist. Ereignisname und Payload werden stabil dokumentiert und enthalten keine unnötig grossen HTML-Inhalte.

Optional für eine spätere Version:

- Sensor für die Zahl neuer Beiträge beim letzten Abruf,
- Schaltfläche für einen manuellen Abruf,
- Reparaturhinweis bei dauerhaft ungültiger Konfiguration,
- Statistik über verworfene Beiträge, ohne die Home-Assistant-Datenbank unnötig zu belasten.

## 8. Umsetzung in Etappen

### Etappe 1: Repository und Integration-Grundgerüst

- HACS-konforme Verzeichnisstruktur anlegen.
- `manifest.json`, `hacs.json`, Konstanten, Übersetzungen und Setup/Unload implementieren.
- Python- und Home-Assistant-Versionen festlegen.
- Entwicklungs-, Test- und Formatierungswerkzeuge konfigurieren.
- Ergebnis: Die leere Integration lässt sich über HACS beziehungsweise manuell installieren und von Home Assistant laden.

### Etappe 2: Feed-Abruf und Parser

- HTTP-Client und Feed-Parser implementieren.
- RSS- und Atom-Beiträge in das gemeinsame Datenmodell überführen.
- `ETag`, `Last-Modified`, Timeouts und sinnvolle Grössenlimits ergänzen.
- Parser-Fixtures für verschiedene reale Feed-Varianten anlegen.
- Ergebnis: Ein Feed kann zuverlässig gelesen und normalisiert werden.

### Etappe 3: Vollständige UI-Konfiguration

- Config Flow zum Hinzufügen eines Feeds erstellen.
- Erreichbarkeit und Parsebarkeit im Dialog validieren.
- Reconfigure-/Options-Flow für Abruf, Filter und Benachrichtigungen erstellen.
- deutsche und englische UI-Texte samt Feldbeschreibungen ergänzen.
- Ergebnis: Kein YAML ist für Einrichtung oder Betrieb erforderlich.

### Etappe 4: Coordinator, Sensor und Persistenz

- `DataUpdateCoordinator` pro Konfigurationseintrag einführen.
- Sensor für den letzten akzeptierten Beitrag erstellen.
- persistente Deduplizierung implementieren.
- Erstabruf- und Neustartverhalten absichern.
- Ergebnis: Neue Beiträge werden genau einmal erkannt und in Home Assistant sichtbar.

### Etappe 5: Filterung

- Einschluss-, Ausschluss-, Alters- und Kategorienfilter implementieren.
- Regex-Validierung in der UI ergänzen.
- Filterentscheidungen mit debug-tauglichen, datensparsamen Logs nachvollziehbar machen.
- Ergebnis: Nur Beiträge, die alle konfigurierten Regeln erfüllen, werden weitergegeben.

### Etappe 6: Benachrichtigungen und Ereignisse

- Auswahl mehrerer `notify`-Entitäten in der UI ermöglichen.
- Einzel- und Sammelversand über `notify.send_message` implementieren.
- Nachrichtenformat und Platzhalter sicher rendern.
- Integrationsereignis für akzeptierte Beiträge auslösen.
- Ergebnis: Gefilterte neue Beiträge können direkt oder über eigene Automationen versendet werden.

### Etappe 7: Qualität, Dokumentation und Release

- Unit- und Integrationsnahe Tests vervollständigen.
- Diagnoseausgabe mit geschwärzten URLs/Zugangsdaten implementieren.
- README mit Installation, UI-Konfiguration, Filterbeispielen, Ereignis und Fehlerbehebung schreiben.
- HACS Action, Hassfest und Tests in GitHub Actions ausführen.
- Icon/Branding, Lizenz, Versionsstrategie und Changelog ergänzen.
- erstes semantisch versioniertes GitHub Release erstellen.
- Ergebnis: installierbare und dokumentierte Version `0.1.0`.

## 9. Teststrategie

### Parser-Tests

- RSS 2.0 und Atom,
- Namespaces und CDATA,
- fehlende GUID, Links oder Datumsangaben,
- HTML in Titel und Beschreibung,
- fehlerhafte Einzelartikel,
- unterschiedliche Zeitzonen und Datumsformate.

### Filter-Tests

- leere Filter,
- Ein- und Ausschlussregeln kombiniert,
- Gross-/Kleinschreibung,
- Regex-Treffer und ungültige Regex,
- Kategorien und Altersgrenzen,
- definierte Priorität, wenn Ein- und Ausschluss gleichzeitig treffen.

### Ablauf-Tests

- erster Abruf ohne Benachrichtigungsflut,
- genau eine Benachrichtigung für einen neuen Artikel,
- keine Wiederholung nach Neustart,
- mehrere neue Artikel in stabiler Reihenfolge,
- HTTP `304 Not Modified`, Timeout und ungültiger Feed,
- Änderung der Optionen und Reload des Konfigurationseintrags,
- mehrere Feeds mit unterschiedlichen Intervallen und Regeln,
- ein fehlgeschlagenes Notification-Ziel bei mehreren Zielen.

### UI- und HACS-Validierung

- vollständige Config-Flow- und Options-Flow-Testabdeckung,
- Übersetzungsschlüssel prüfen,
- HACS-Validierung und Hassfest,
- Installation und Update in einer echten Home-Assistant-Testinstanz,
- Deinstallation ohne zurückbleibende Listener oder Tasks.

## 10. Abnahmekriterien für Version 0.1.0

Die erste Version gilt als fertig, wenn:

- mindestens drei Feeds parallel über die UI eingerichtet werden können,
- RSS 2.0 und Atom verarbeitet werden,
- alle Einstellungen ohne YAML änderbar sind,
- Ein- und Ausschlussfilter nachweislich funktionieren,
- neue passende Beiträge an mehrere auswählbare `notify`-Entitäten gesendet werden können,
- vorhandene Beiträge bei der Erstinstallation standardmässig nicht versendet werden,
- Beiträge nach Neustart nicht doppelt versendet werden,
- ein defekter Feed die anderen Feeds nicht beeinträchtigt,
- automatisierte Tests, HACS-Validierung und Hassfest erfolgreich laufen,
- Installation, Konfiguration, Filterlogik und Benachrichtigungen dokumentiert sind.

## 11. Bewusst verschobene Erweiterungen

Diese Punkte sind sinnvoll, aber nicht für die erste Version erforderlich:

- OPML-Import und -Export,
- gemeinsame globale Filterprofile für mehrere Feeds,
- vollständige Jinja-Templates statt einfacher sicherer Platzhalter,
- Download und Versand von Bildern oder Anhängen,
- Volltextabruf der verlinkten Webseite,
- WebSub/Push statt Polling,
- Verwaltung vieler Feeds als Subentries eines einzigen Konfigurationseintrags,
- Rückwirkendes erneutes Verarbeiten alter Beiträge.

## 12. Offizielle Referenzen

- [HACS-Anforderungen für Integrationen](https://www.hacs.xyz/docs/publish/integration/)
- [Allgemeine HACS-Publishing-Anforderungen](https://www.hacs.xyz/docs/publish/start/)
- [Home Assistant Config Flow](https://developers.home-assistant.io/docs/core/integration/config_flow/)
- [Home Assistant Options Flow](https://developers.home-assistant.io/docs/core/integration/options_flow/)
- [Home Assistant DataUpdateCoordinator und Datenabruf](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Home Assistant `notify.send_message`](https://www.home-assistant.io/actions/notify.send_message/)
- [Home Assistant Integrationsstruktur](https://developers.home-assistant.io/docs/creating_integration_file_structure/)
