-- Module:تصنيف بقالب
-- Replacement for Template:تصنيف بقالب
-- Shows category links for template documentation
-- Usage: {{#invoke:تصنيف بقالب|main|اسم تصنيف|من معلم}}

local p = {}

function p.main(frame)
	local args = frame.args
	local catNames = args["اسم تصنيف"] or args[1] or ""
	local fromParams = args["من معلم"] or args[2] or ""

	local result = {}
	local isRoot = frame:callParserFunction("ISROOTPAGE") ~= ""

	if fromParams == "" then
		-- Simple mode: just show category links
		local cats = mw.text.split(catNames, "،")
		local links = {}
		for _, cat in ipairs(cats) do
			cat = mw.text.trim(cat)
			if cat ~= "" then
				table.insert(links, "<samp>[[:تصنيف:" .. cat .. "|" .. cat .. "]]</samp>")
			end
		end
		result[#result + 1] = table.concat(links, " و ")

		if isRoot then
			for _, cat in ipairs(cats) do
				cat = mw.text.trim(cat)
				if cat ~= "" then
					result[#result + 1] = "{{#set:يصنف على=تصنيف:" .. cat .. "}}"
				end
			end
		end
	else
		-- Pattern mode: derive category names from parameter names
		local cats = mw.text.split(catNames, "،")
		local params = mw.text.split(fromParams, "،")
		local links = {}

		for i, cat in ipairs(cats) do
			cat = mw.text.trim(cat)
			local param = params[i] and mw.text.trim(params[i]) or ""
			if cat ~= "" then
				local display = mw.ustring.gsub(cat, "@@", "<var>" .. param .. "</var>")
				table.insert(links, "<samp>" .. display .. "</samp>")
			end
		end
		result[#result + 1] = table.concat(links, " و ")
	end

	if isRoot then
		result[#result + 1] = "[[تصنيف:قوالب تصنيف]]"
	end

	return table.concat(result, "")
end

return p
