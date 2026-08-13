# RSS Parser für Home Assistant

**Deutsch** | [English](README.md)

> **Hinweis:** Dieser Code wurde mit Unterstützung von KI generiert.

RSS Parser ist eine benutzerdefinierte Home-Assistant-Integration zum Abrufen, Filtern und Versenden von RSS- und Atom-Beiträgen. Sämtliche Einstellungen werden über die Home-Assistant-Oberfläche vorgenommen.

## Funktionen

- Beliebig viele Feeds – die Integration wird einmal pro Feed hinzugefügt
- Unterstützung für RSS 2.0 und Atom
- Ein- und Ausschlussfilter für Texte und Kategorien
- Optionale reguläre Ausdrücke, Beachtung der Gross-/Kleinschreibung und Altersgrenze
- Persistente Duplikaterkennung über Home-Assistant-Neustarts hinweg
- Einzel- oder Sammelbenachrichtigungen über `notify.send_message`
- Sensor mit dem letzten passenden Beitrag
- Ereignis `rss_parser_new_entry` für eigene Automationen
- Bedingte HTTP-Abfragen mit `ETag` und `Last-Modified`
- Deutsche und englische Benutzeroberfläche

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mbraunschweiler&repository=HA-RssFeedParser)

### Als benutzerdefiniertes HACS-Repository

1. HACS in Home Assistant öffnen.
2. `https://github.com/mbraunschweiler/HA-RssFeedParser` als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen.
3. Nach **RSS Parser** suchen und die Integration installieren.
4. Home Assistant neu starten.
5. **Einstellungen > Geräte & Dienste > Integration hinzufügen** öffnen und **RSS Parser** auswählen.

### Manuelle Installation

Den Ordner `custom_components/rss_parser` in das Verzeichnis `custom_components` der Home-Assistant-Konfiguration kopieren. Anschliessend Home Assistant neu starten und die Integration über die Benutzeroberfläche hinzufügen.

## Konfiguration

Für jeden Feed wird ein eigener Integrationseintrag erstellt. Der Einrichtungsdialog fragt nach:

- einem Anzeigenamen,
- der HTTP- oder HTTPS-Adresse des Feeds,
- der gewünschten Behandlung bereits vorhandener Beiträge beim ersten Abruf.

Die Adresse wird abgerufen und der Inhalt als RSS- oder Atom-Feed geprüft, bevor der Eintrag gespeichert wird. URLs mit eingebetteten Zugangsdaten werden absichtlich abgelehnt, damit keine Zugangsdaten in Diagnosen oder Protokollen erscheinen.

Über **Konfigurieren** lassen sich Abrufintervall, Filter und Benachrichtigungen ändern. Mit **Neu konfigurieren** können Name und Feed-URL angepasst werden.

## Filter

Ein- und Ausschlusswerte können durch Kommas oder Zeilenumbrüche getrennt werden. Durchsucht werden Titel, Zusammenfassung, Autor, Link und Kategorien eines Beitrags.

Die Regeln werden in dieser Reihenfolge angewendet:

1. Bereits bekannte Beiträge ignorieren.
2. Maximales Beitragsalter prüfen.
3. Text-Ausschlussregeln anwenden.
4. Text-Einschlussregeln anwenden.
5. Kategorie-Ausschlüsse und -Einschlüsse anwenden.

Eine Ausschlussregel hat immer Vorrang. Leere Einschlussfelder akzeptieren jeden Beitrag. Wenn reguläre Ausdrücke aktiviert sind, wird jeder durch Komma oder Zeilenumbruch getrennte Wert als eigener Ausdruck interpretiert und vor dem Speichern geprüft.

Auch abgelehnte Beiträge werden als gesehen gespeichert. Änderungen an Filtern gelten deshalb für neue Beiträge und verarbeiten nicht rückwirkend bereits bekannte Einträge.

## Benachrichtigungen

Benachrichtigungen können aktiviert und an eine oder mehrere Entitäten aus der Domain `notify` gesendet werden. RSS Parser verwendet dafür die Home-Assistant-Aktion `notify.send_message`.

Benachrichtigungsintegrationen, die nur ältere Aktionen wie `notify.mobile_app_name` und keine entsprechende `notify`-Entität bereitstellen, werden in Version 0.1.0 noch nicht unterstützt.

Für Titel und Nachricht stehen folgende sichere Platzhalter zur Verfügung:

- `{title}` – Titel des Beitrags
- `{link}` – Link zum Beitrag
- `{summary}` – Zusammenfassung
- `{author}` – Autor
- `{feed_name}` – konfigurierter Feed-Name
- `{published}` – Veröffentlichungszeitpunkt

Es werden keine Jinja-Ausdrücke ausgewertet.

## Ereignis für Automationen

Jeder neue passende Beitrag löst das Ereignis `rss_parser_new_entry` aus. Dies geschieht unabhängig davon, ob der direkte Benachrichtigungsversand aktiviert ist.

Beispiel:

```yaml
triggers:
  - trigger: event
    event_type: rss_parser_new_entry
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.feed_name == 'Home Assistant Blog' }}"
actions:
  - action: persistent_notification.create
    data:
      title: "{{ trigger.event.data.title }}"
      message: "{{ trigger.event.data.link }}"
```

Das Ereignis enthält:

- `entry_id`
- `feed_name`
- `title`
- `link`
- `summary`
- `author`
- `categories`
- `published`

## Sicherheit und Begrenzungen

- Minimales Abrufintervall: 5 Minuten
- Maximale Feed-Antwortgrösse: 5 MiB
- Gespeicherte Beitrags-IDs pro Feed: 500
- Maximal verarbeitete passende Beiträge pro Abruf: 1 bis 100
- Vorhandene Beiträge werden standardmässig beim Einrichten nicht versendet

Wenn mehr passende Beiträge eintreffen als die konfigurierte Begrenzung erlaubt, werden nur die neuesten Beiträge innerhalb der Begrenzung ausgegeben. Alle beobachteten IDs werden dennoch als verarbeitet markiert, damit später keine unerwartete Benachrichtigungsflut entsteht.

## Entwicklung

Die lokalen Testabhängigkeiten installieren und die Prüfungen ausführen:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Pull Requests werden mit pytest, Ruff, Hassfest und der HACS-Validierung geprüft.

## Repository

Quellcode, Releases und Fehlermeldungen werden unter [mbraunschweiler/HA-RssFeedParser](https://github.com/mbraunschweiler/HA-RssFeedParser) verwaltet.

## Lizenz

MIT
