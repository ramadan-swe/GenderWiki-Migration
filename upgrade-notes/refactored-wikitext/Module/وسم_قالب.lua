-- Module:وسم قالب
-- Replacement for Template:وسم قالب
-- Generates template usage syntax from parameter specs
-- Usage: {{#invoke:وسم قالب|main|بيان_معلم|اسم القالب|مطوّل|بالتعويض}}
-- where every بيان_معلم is a "[(ordinal):]name[:(cardinality)]"

local function parseParam(str)
	if not str or str == "" then
		return nil, "", nil
	end
	local ordinal, name, card = mw.ustring.match(str, "^(%d+):(.+):([1؟%+%*])$")
	if ordinal then return ordinal, name, card end
	name, card = mw.ustring.match(str, "^(.+):([1؟%+%*])$")
	if name then return nil, name, card end
	ordinal, name = mw.ustring.match(str, "^(%d+):(.+)$")
	if ordinal then return ordinal, name, nil end
	return nil, str, nil
end

local function cardinalitySymbol(card)
	if card == "*" then return "&lowast;" end
	return card or ""
end

local p = {}

function p.main(frame)
	local args = frame.args
	local full = args["مطوّل"] or "لا"
	local subst = args["بالتعويض"] or "لا"
	local templateName = args["اسم القالب"] or args[2] or ""
	local paramSpec = args["بيان_معلم"] or args[1] or ""

	if templateName == "" then
		templateName = mw.title.getCurrentTitle().text
	end
	templateName = mw.ustring.gsub(templateName, " ", "_")

	-- Parse all parameter specs
	local paramNames = {}
	local specs = mw.text.split(paramSpec, "،")
	for _, spec in ipairs(specs) do
		if spec ~= "" then
			local _, name = parseParam(spec)
			if name and name ~= "" then
				table.insert(paramNames, name)
			end
		end
	end

	local result = "{{"

	if subst == "نعم" then
		result = result .. "subst:"
	end

	result = result .. templateName

	for _, name in ipairs(paramNames) do
		result = result .. "|" .. name .. "="
	end

	result = result .. "}}"

	if full == "نعم" then
		result = "<code style=\"display: block; width: 50%;\">" .. result .. "</code>"
	else
		result = "<code>" .. result .. "</code>"
	end

	return result
end

return p
