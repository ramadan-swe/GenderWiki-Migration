-- Module:Variables
-- Replacement for the Variables extension (#vardefine, #var, #vardefineecho)
-- Usage: {{#invoke:Variables|define|name=value}}  → sets variable, returns value
--        {{#invoke:Variables|var|name|default}}     → gets variable value
--        {{#invoke:Variables|varecho|name=value}}   → sets and prints value

local p = {}
local vars = {}

function p.define(frame)
	local args = frame.args
	local name = args[1] or ""
	local value = args[2] or ""
	vars[name] = value
	return value
end

function p.var(frame)
	local args = frame.args
	local name = args[1] or ""
	local default = args[2] or ""
	if vars[name] ~= nil then
		return vars[name]
	end
	return default
end

function p.varecho(frame)
	return p.define(frame)
end

function p.set(frame)
	local name = frame.args[1] or ""
	local value = frame.args[2] or ""
	vars[name] = value
	return ""
end

function p.get(frame)
	local name = frame.args[1] or ""
	return vars[name] or ""
end

p.defineecho = p.varecho
p.vardefine = p.define
p.varexists = p.var

return p
