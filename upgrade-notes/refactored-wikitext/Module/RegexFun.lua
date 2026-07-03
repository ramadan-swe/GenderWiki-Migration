-- Module:RegexFun
-- Replacement for RegexFun extensions (#regex, #regex_var)
-- Provides mw.ustring-based equivalents of the specific patterns used in the wiki

local p = {}

-- Pattern 1: Template parameter format parser
-- Used by: بيان معلم, وسم قالب
-- Original: /^(?:(\d)*:)?([\pL\pM\s]+)(?::([1؟\+\*])?)?$/Uu
-- Matches: "ordinal:name:cardinality", "name:cardinality", "name"
-- Returns: ordinal (string|nil), name (string), cardinality (string|nil)
function p.parseParamFormat(str)
	if not str or str == "" then
		return nil, "", nil
	end
	-- Try: ordinal:name:cardinality → "1:اسم:+"
	local ordinal, name, card = mw.ustring.match(str, "^(%d+):(.+):([1؟%+%*])$")
	if ordinal then
		return ordinal, name, card
	end
	-- Try: name:cardinality → "اسم:+"
	local name, card = mw.ustring.match(str, "^(.+):([1؟%+%*])$")
	if name then
		return nil, name, card
	end
	-- Try: ordinal:name → "1:اسم"
	local ordinal, name = mw.ustring.match(str, "^(%d+):(.+)$")
	if ordinal then
		return ordinal, name, nil
	end
	-- Plain name
	return nil, str, nil
end

-- Pattern 2: Deletion list word stripping
-- Used by: اسم منظّمة مجرّد
-- Strips the first word if it's in the deletion list
-- Original: /(?:word1|word2|...)\s+(.+)/
function p.stripDeletionWord(str, deletionList)
	if not str or str == "" then
		return str
	end
	local words = mw.text.split(deletionList, "،")
	for _, word in ipairs(words) do
		local rest = mw.ustring.match(str, "^" .. word .. "%s(.+)$")
		if rest then
			return rest
		end
	end
	return str
end

-- Generic: apply a Lua pattern match and return all captures
function p.match(frame)
	local args = frame.args
	local str = args[1] or ""
	local pattern = args[2] or ""
	local idx = tonumber(args[3]) or 1
	local captures = { mw.ustring.match(str, pattern) }
	return captures[idx] or ""
end

return p
