-- Module:صفحة تصنيف مصدر وثائق
-- Replacement for Template:صفحة تصنيف مصدر وثائق
-- Generates a source category page with SMW data display
-- Usage: {{#invoke:صفحة تصنيف مصدر وثائق|main}}

local p = {}

function p.main(frame)
	local thisTitle = mw.title.getCurrentTitle()
	local pageName = thisTitle.text  -- "وثائق مصدرها <name>"

	-- Extract source name (strip "وثائق مصدرها " prefix = 13 chars)
	local sourceName = mw.ustring.sub(pageName, 14)

	-- Query SMW data for the source
	local sourceData = {}
	local queryResult = mw.smw.ask({
		"[" .. sourceName .. "]",
		"?شعار",
		"?فئة_المنظّمة",
		"?سنة_التأسيس"
	})

	if queryResult and #queryResult > 0 then
		local data = queryResult[1]
		sourceData.logo = (data["شعار"] and data["شعار"][1]) or ""
		sourceData.category = (data["فئة_المنظّمة"] and data["فئة_المنظّمة"][1]) or ""
		sourceData.year = (data["سنة_التأسيس"] and data["سنة_التأسيس"][1]) or ""
	end

	-- Build the logo HTML
	local logoHtml = ""
	if sourceData.logo ~= "" then
		logoHtml = "[[ملف:" .. sourceData.logo .. "|120px|يسار]]"
	else
		logoHtml = "[[ملف:Circle-icons-document.svg|120px|يسار]]"
	end

	-- Build the result
	local result = ""
	result = result .. '<div style="width: 33%%; border: #831a03 solid thin; padding: .5em;">'
	result = result .. '<span style="vertical-align: middle">' .. logoHtml .. '</span>'
	result = result .. 'وثائق مصدرها [[' .. sourceName .. ']]'
	result = result .. '<br/>'
	if sourceData.category ~= "" then
		result = result .. sourceData.category
	end
	if sourceData.year ~= "" then
		result = result .. " تأسّست سنة " .. sourceData.year
	end
	result = result .. '</div>'

	result = result .. "[[تصنيف:وثائق حسب المصدر|" .. sourceName .. "]]"
	result = result .. "[[تصنيف:تصنيفات بقوالب]]"
	result = result .. "[[تصنيف:صفحات تصنيفات مولّدة تلقائيا]]"

	return result
end

return p
