-- Module:بيان معلم
-- Replacement for Template:بيان معلم
-- Formats a template parameter documentation entry
-- Usage: {{#invoke:بيان معلم|main|نسق|وصف|استبدائية|خصيصة}}
-- where نسق = "[(ordinal):]name[:(cardinality)]"

local p = {}

local cardinalityLabels = {
	["1"] = "ضروري؛ قيمة واحدة",
	["+"] = "ضروري؛ قيمة أو أكثر",
	["؟"] = "اختياري؛ قيمة واحدة",
	["*"] = "اختياري؛ قيمة أو أكثر",
}

function p.main(frame)
	local args = frame.args
	local paramFormat = args[1] or ""
	local description = args[2] or ""
	local default = args[3] or ""
	local property = args[4] or ""

	-- Parse the parameter format
	local ordinal, name, cardinality = p.parseFormat(paramFormat)

	local result = ";"
	result = result .. (name or "")

	-- Add cardinality suffix
	if cardinality then
		if cardinality == "*" then
			result = result .. ":&lowast;"
		else
			result = result .. ":" .. cardinality
		end
	end

	result = result .. ":"
	result = result .. description

	-- Add cardinality label
	if cardinality then
		result = result .. " " .. mw.html.create("span"):css("text-decoration", "underline"):wikitext(cardinalityLabels[cardinality] or "")
	end

	result = result .. "."

	-- Add default value note
	if default ~= "" then
		result = result .. " القيمة الاستبدادية \"<kbd>" .. default .. "</kbd>\"."
	end

	-- Add property note
	if property ~= "" then
		result = result .. " يُعيّن قيمة [[خاصية:" .. property .. "]]."
	end

	return result
end

function p.parseFormat(str)
	if not str or str == "" then
		return nil, "", nil
	end

	-- ordinal:name:cardinality → "1:اسم:+"
	local ordinal, name, card = mw.ustring.match(str, "^(%d+):(.+):([1؟%+%*])$")
	if ordinal then
		return ordinal, name, card
	end

	-- name:cardinality → "اسم:+"
	name, card = mw.ustring.match(str, "^(.+):([1؟%+%*])$")
	if name then
		return nil, name, card
	end

	-- ordinal:name → "1:اسم"
	ordinal, name = mw.ustring.match(str, "^(%d+):(.+)$")
	if ordinal then
		return ordinal, name, nil
	end

	-- plain name
	return nil, str, nil
end

return p
