-- Module:صفحة تصنيف عقد
-- Replacement for Template:صفحة تصنيف عقد
-- Shows links to decade categories for related content types
-- Usage: {{#invoke:صفحة تصنيف عقد|main|أنواع المحتوى|مميز العقد}}
-- حيث أنواع المحتوى مثال: "وثائق،كتب،أفلام،أغاني"
-- و مميز العقد مثال: "201"

local p = {}

function p.main(frame)
	local args = frame.args
	local contentTypes = args[1] or ""
	local decadeKey = args[2] or ""

	if decadeKey == "" then return "" end

	local decadeLabel = mw.ustring.sub(decadeKey, 1, 3) .. "𝘹"
	local types = mw.text.split(contentTypes, "،")
	local links = {}

	for _, t in ipairs(types) do
		if t ~= "" then
			local catName = t .. " " .. decadeLabel
			local catTitle = mw.title.new("تصنيف:" .. catName)
			if catTitle and catTitle.exists then
				table.insert(links, "* [[:تصنيف:" .. catName .. "]]")
			end
		end
	end

	if #links == 0 then return "" end

	return "طالع كذلك:\n" .. table.concat(links, "\n")
end

return p
