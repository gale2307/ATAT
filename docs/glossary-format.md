# LoL terminology glossary format

## Purpose

The glossary serves two functions:
1. **STT prompting**: Helps Whisper recognize domain terms by providing them as initial prompt context
2. **Translation term intervention**: Passed to Qwen-MT's `terms` parameter or used as constraints in NLLB/LLM translation

## File format

JSON file at `backend/app/glossary/lol_terms.json`:

```json
{
  "version": "1.0",
  "last_updated": "2026-03-24",
  "categories": {
    "champions": [
      {
        "ko": "오리아나",
        "en": "Orianna",
        "aliases_ko": ["오리"],
        "aliases_en": ["Ori"]
      },
      {
        "ko": "아지르",
        "en": "Azir",
        "aliases_ko": [],
        "aliases_en": []
      }
    ],
    "abilities": [
      {
        "ko": "쇼크웨이브",
        "en": "Shockwave",
        "champion": "Orianna",
        "key": "R"
      },
      {
        "ko": "황제의 분할",
        "en": "Emperor's Divide",
        "champion": "Azir",
        "key": "R"
      }
    ],
    "items": [
      {
        "ko": "무한의 대검",
        "en": "Infinity Edge",
        "aliases_ko": ["무대"]
      },
      {
        "ko": "징후의 검",
        "en": "Blade of the Ruined King",
        "aliases_ko": ["몰왕검"]
      }
    ],
    "players": [
      {
        "ko": "페이커",
        "en": "Faker",
        "real_name_ko": "이상혁",
        "team": "T1"
      },
      {
        "ko": "구마유시",
        "en": "Gumayusi",
        "real_name_ko": "이민형",
        "team": "T1"
      }
    ],
    "teams": [
      {
        "ko": "한화생명",
        "en": "Hanwha Life Esports",
        "abbreviation": "HLE"
      },
      {
        "ko": "젠지",
        "en": "Gen.G",
        "abbreviation": "GEN"
      }
    ],
    "game_terms": [
      {"ko": "갱킹", "en": "ganking"},
      {"ko": "갱", "en": "gank"},
      {"ko": "드래곤 소울", "en": "Dragon Soul"},
      {"ko": "바론 나쉬어", "en": "Baron Nashor"},
      {"ko": "바론", "en": "Baron"},
      {"ko": "장로 드래곤", "en": "Elder Dragon"},
      {"ko": "미니언", "en": "minion"},
      {"ko": "포탑", "en": "turret"},
      {"ko": "억제기", "en": "inhibitor"},
      {"ko": "넥서스", "en": "Nexus"},
      {"ko": "텔레포트", "en": "Teleport"},
      {"ko": "점멸", "en": "Flash"},
      {"ko": "정글러", "en": "jungler"},
      {"ko": "원딜", "en": "ADC"},
      {"ko": "서폿", "en": "support"},
      {"ko": "미드", "en": "mid"},
      {"ko": "탑", "en": "top"},
      {"ko": "봇", "en": "bot"},
      {"ko": "로밍", "en": "roaming"},
      {"ko": "스플릿 푸쉬", "en": "split push"},
      {"ko": "팀파이트", "en": "teamfight"},
      {"ko": "에이스", "en": "ace"},
      {"ko": "펜타킬", "en": "pentakill"},
      {"ko": "퍼스트 블러드", "en": "first blood"}
    ]
  }
}
```

## Usage in STT (Whisper initial prompt)

Whisper accepts an `initial_prompt` parameter that biases the decoder toward expected vocabulary. Build a prompt from the glossary:

```python
def build_whisper_prompt(glossary: dict) -> str:
    """Build initial prompt for Whisper from glossary terms."""
    terms = []
    for category in glossary["categories"].values():
        for term in category:
            if isinstance(term, dict) and "ko" in term:
                terms.append(term["ko"])
    # Whisper prompt has max 224 tokens — prioritize most common terms
    prompt = ", ".join(terms[:100])
    return prompt
```

## Usage in translation (Qwen-MT terms parameter)

```python
def build_qwen_terms(glossary: dict) -> list[dict]:
    """Build Qwen-MT terms list from glossary."""
    terms = []
    for category in glossary["categories"].values():
        for entry in category:
            if isinstance(entry, dict) and "ko" in entry and "en" in entry:
                terms.append({"source": entry["ko"], "target": entry["en"]})
                # Also add aliases
                for alias in entry.get("aliases_ko", []):
                    terms.append({"source": alias, "target": entry["en"]})
    return terms
```

## Maintenance

The glossary needs updating when:
- New champions are released (~every 2-4 weeks)
- Items are reworked in major patches
- New players join LCK rosters (between splits)
- New game mechanics are introduced (seasonal changes)

Data sources for updates:
- Riot Games API / Data Dragon for champion and item data
- Leaguepedia/Fandom wiki for player and team data
- Korean LoL Wiki (namu.wiki) for Korean terminology
