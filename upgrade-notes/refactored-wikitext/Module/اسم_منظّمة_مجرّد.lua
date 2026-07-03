-- Module:اسم منظّمة مجرّد
-- Replacement for Template:اسم منظّمة مجرّد
-- Strips leading articles and generic organizational words from an organization name
-- Usage: {{#invoke:اسم منظّمة مجرّد|main|اسم المنظّمة}}
-- Returns: stripped singular word

local p = {}

-- Words to strip from the beginning of the name
local deletionList = {"مبادرة", "مؤسسة", "منظمة", "مشروع"}

-- Recursively strip leading articles and deletion words
local function stripName(name)
	name = mw.text.trim(name or "")
	if name == "" then return "" end

	-- Get the first word
	local firstWord = mw.ustring.match(name, "^([^%s]+)")

	if not firstWord then return name end

	-- If it starts with definite article "ال", strip it
	if mw.ustring.match(firstWord, "^ال") then
		return mw.ustring.sub(firstWord, 3)
	end

	-- Check if the first word is in the deletion list
	for _, word in ipairs(deletionList) do
		if firstWord == word then
			-- Strip the word and recurse
			local rest = mw.ustring.match(name, "^" .. word .. "%s+(.+)$")
			if rest then
				return stripName(rest)
			end
		end
	end

	-- No match, return the first word
	return firstWord
end

function p.main(frame)
	local args = frame.args
	local name = args[1] or ""
	return stripName(name)
end

return p
