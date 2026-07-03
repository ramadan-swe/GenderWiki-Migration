# Refactored Wikitext: Variables & RegexFun → Scribunto

## Overview

This directory contains replacement Scribunto modules that eliminate the dependency on the archived [Variables](https://www.mediawiki.org/wiki/Extension:Variables) and [RegexFun](https://www.mediawiki.org/wiki/Extension:RegexFun) extensions.

Both extensions are deprecated/archived. Variables was merged into Scribunto patterns (local Lua variables). RegexFun cannot be loaded via `wfLoadExtension` (uses `require_once`) and its parser hook `$mExtRegexFun` is deprecated since MW 1.42. RegexFun is also incompatible with the DiscussionTools extension.

| File | Usage | Replaces |
|---|---|---|
| `Module/Variables.lua` | Shared | `#vardefine:`, `#var:`, `#vardefineecho:` |
| `Module/RegexFun.lua` | Shared | `#regex:`, `#regex_var:` (pattern-specific) |
| `Module/بيان_معلم.lua` | `{{بيان معلم}}` | `#regex:`, `#regex_var:` in parameter format docs |
| `Module/وسم_قالب.lua` | `{{وسم قالب}}` | `#regex:`, `#regex_var:` in template usage syntax |
| `Module/اسم_منظّمة_مجرّد.lua` | `{{اسم منظّمة مجرّد}}` | `#vardefine:`, `#var:`, `#regex:` in name stripping |
| `Module/تصنيف_بقالب.lua` | `{{تصنيف بقالب}}` | `#vardefine:`, `#var:` in iteration pattern |
| `Module/تصنيف_نوع_صورة.lua` | `{{تصنيف نوع صورة}}` | `#vardefine:`, `#var:` in image type→category map |
| `Module/تصنيف_نوع_وثيقة.lua` | `{{تصنيف نوع وثيقة}}` | `#vardefine:`, `#var:` in doc type→category map |
| `Module/تعرّف_على_نوع_الوثيقة.lua` | `{{تعرّف على نوع الوثيقة}}` | `#vardefineecho:`, `#vardefine:` in class determination |
| `Module/صفحة_تصنيف_عقد.lua` | `{{صفحة تصنيف عقد}}` | `#vardefine:`, `#var:` in decade category links |
| `Module/صفحة_تصنيف_مصدر_وثائق.lua` | `{{صفحة تصنيف مصدر وثائق}}` | `#vardefine:`, `#var:` in source category page |
| `Module/بيانات_وثيقة.lua` | `{{بيانات وثيقة}}` | `#vardefine:`, `#var:` in doc infobox |

## Usage Counts

| Pattern | Total | Pages (latest rev) |
|---|---|---|
| `#var:` | 494 | 8 |
| `#vardefine:` | 245 | 9 |
| `#regex_var:` | 34 | 2 |
| `#regex:` | 16 | 3 |
| `#vardefineecho:` | 15 | 2 |
| `#varexists:` | 0 | 0 |
| `#var_final:` | 0 | 0 |
| `#regexall:` | 0 | 0 |
| `#regexquote:` | 0 | 0 |

## Migration Strategy

### Step 1: Create Scribunto modules

Copy all `Module/*.lua` files to the wiki's `Module:` namespace pages.
Verify syntax with `{{#invoke:<name>|main|<params>}}`.

### Step 2: Rewrite affected templates

Each template that currently uses `#vardefine`/`#var`/`#regex` should be rewritten to call the corresponding Scribunto module via `{{#invoke:ModuleName|main|...}}`.

**Simple case** (e.g. `تصنيف نوع صورة`):
```wikitext
<!-- OLD -->
{{#vardefine:نوع_الصورة|{{#switch:{{{1|}}}|...}}}}
[[تصنيف:{{#var:نوع_الصورة}}]]

<!-- NEW -->
[[تصنيف:{{#invoke:تصنيف نوع صورة|main|{{{1|}}}}}]]{{#createpageifnotex:تصنيف:{{#invoke:تصنيف نوع صورة|main|{{{1|}}}}}}}|<nowiki>{{صفحة_تصنيف_نوع_صور}}</nowiki>}}
```

**Variables replacement** (e.g. `صفحة تصنيف مصدر وثائق`):
Replace `{{#vardefine:X|...}}{{#var:X}}` with local function calls. The entire template logic is wrapped in a single `#invoke`.

**Regex replacement** (e.g. `بيان معلم`):
Translate PCRE patterns to Lua `mw.ustring.match()` patterns. For the parameter format `[(ordinal):]name[:(cardinality)]`, use the `RegexFun.parseParamFormat()` helper.

### Step 3: Verify

Test each template after migration:
1. `{{بيان معلم|1:اسم:+}}` should render "اسم" with cardinality decoration
2. `{{تصنيف نوع صورة|صورة شخص}}` should return "صور أشخاص"
3. `{{اسم منظّمة مجرّد|المبادرة المصرية}}` should return "مبادرة"
4. `{{وسم قالب|1:اسم:+|قالب:مثال}}` should render `<code>{{مثال|اسم=}}</code>`

## Notes

- `بيانات وثيقة` is the most complex template. Its current `#vardefine:اسم_التصنيف`/`#var:اسم_التصنيف` pattern relies on side-effect variable sharing between `تعرّف على نوع الوثيقة` and the parent template. The Scribunto module removes this coupling by calling the type module directly.
- `User:أحمد/تجربة` and `User:أحمد/مخبر/قالب:تصنيف مصدر وثائق` are user sandbox/test pages. They are not production templates and can be migrated manually or ignored.
- `#varexists:`, `#var_final:`, `#regexall:`, `#regexquote:` have zero usage across the entire wiki and require no migration.
- After migration, remove `RegexFun` and `Variables` from `Extensions.conf` and delete their extension directories.

## File Structure

```
refactored-wikitext/
├── README.md
├── Module/
│   ├── Variables.lua
│   ├── RegexFun.lua
│   ├── بيان_معلم.lua
│   ├── وسم_قالب.lua
│   ├── اسم_منظّمة_مجرّد.lua
│   ├── تصنيف_بقالب.lua
│   ├── تصنيف_نوع_صورة.lua
│   ├── تصنيف_نوع_وثيقة.lua
│   ├── تعرّف_على_نوع_الوثيقة.lua
│   ├── صفحة_تصنيف_عقد.lua
│   ├── صفحة_تصنيف_مصدر_وثائق.lua
│   └── بيانات_وثيقة.lua
├── Template/
│   ├── اسم_منظّمة_مجرّد.wikitext
│   ├── بيان_معلم.wikitext
│   ├── بيانات_وثيقة.wikitext
│   ├── تصنيف_بقالب.wikitext
│   ├── تصنيف_نوع_صورة.wikitext
│   ├── تصنيف_نوع_وثيقة.wikitext
│   ├── تعرّف_على_نوع_الوثيقة.wikitext
│   ├── صفحة_تصنيف_عقد.wikitext
│   ├── صفحة_تصنيف_مصدر_وثائق.wikitext
│   └── وسم_قالب.wikitext
└── User/
    └── أحمد/
        ├── تجربة.wikitext
        └── مخبر/
            └── قالب_تصنيف_مصدر_وثائق.wikitext
```
