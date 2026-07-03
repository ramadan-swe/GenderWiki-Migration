-- Module:بيانات وثيقة
-- Replacement for Template:بيانات وثيقة
-- Renders a document metadata infobox with categories
-- Uses Module:تعرّف على نوع الوثيقة for type classification
-- Usage: {{#invoke:بيانات وثيقة|main|نوع الوثيقة|...}}

local p = {}

function p.main(frame)
	local args = frame.args
	local docType = args["نوع الوثيقة"] or args[1] or ""

	-- Determine category name and class via تعرّف على نوع الوثيقة
	local typeModule = require("Module:تعرّف على نوع الوثيقة")
	local typeResult = typeModule.main(frame)  -- "cat␟class"
	local catName, docClass = mw.text.split(typeResult, "␟")
	catName = catName or "وثائق أنواعها غير معيّنة"
	docClass = docClass or "وثيقة"

	local source = args["المصدر"] or ""
	local author = args["مؤلف"] or ""
	local editor = args["محرر"] or ""
	local lang = args["لغة"] or ""
	local pubDate = args["تاريخ النشر"] or ""
	local url = args["مسار الاسترجاع"] or ""
	local accessDate = args["تاريخ الاسترجاع"] or ""
	local archive = args["نسخة أرشيفية"] or ""
	local isTranslation = args["هل ترجمة"] or args["أمترجمة"] or "لا"
	local translator = args["مترجم"] or ""
	local origLang = args["لغة الأصل"] or ""
	local origTitle = args["العنوان الأصلي"] or ""
	local origPubDate = args["تاريخ نشر الأصل"] or ""
	local arabicTitle = args["بالعربية"] or args["ترجمة"] or ""
	local note = args["ملاحظة"] or ""
	local subTemplates = args["قوالب فرعية"] or ""
	local borderColor = args["لون الإطار"] or "grey"
	local origText = args["النص الأصلي"] or ""

	local result = {}

	-- SMW set
	result[#result + 1] = "{{#set:نوع ال" .. docClass .. "=" .. docType .. "}}"

	-- Box
	result[#result + 1] = '<div lang="ar" style="direction: rtl; border: ' .. borderColor .. ' solid 5pt; padding: .5em; border-radius: 20px;">'

	-- Header with logo
	local logo = "[[ملف:Circle-icons-document.svg|240px|يسار]]"
	if source ~= "" then
		logo = "{{صورة_وإلا_بدل|صورة={{#show:" .. source .. "|?شعار|link=none}}|بدل=Circle-icons-document.svg|تنسيق=240px|يسار}}"
	end
	result[#result + 1] = '<span style="vertical-align: middle">' .. logo .. '</span>'

	-- Table
	result[#result + 1] = '{| style="text-align: right;"'
	result[#result + 1] = '|+ ' .. docType

	if args["العنوان"] and args["العنوان"] ~= "" then
		result[#result + 1] = "{{صف_معلم_مشروط|العنوان|" .. args["العنوان"] .. "}}"
	end
	if author ~= "" then
		local smw = mw.text.split(author, "،")
		local links = {}
		for _, a in ipairs(smw) do
			table.insert(links, "[[" .. mw.text.trim(a) .. "]]")
		end
		result[#result + 1] = "{{صف_معلم_ضروري|تأليف|" .. author .. "|" .. table.concat(links, " و ") .. "}}"
	end
	-- ... (remaining rows use the existing sub-templates since they don't use Variables/RegexFun)

	result[#result + 1] = "|}"

	-- Note
	if note ~= "" then
		result[#result + 1] = note
	end

	result[#result + 1] = subTemplates

	result[#result + 1] = '</div>'

	-- Categories
	result[#result + 1] = "[[" .. docClass .. "]]"
	result[#result + 1] = "[[تصنيف:" .. catName .. "]]"

	return table.concat(result, "\n")
end

return p
