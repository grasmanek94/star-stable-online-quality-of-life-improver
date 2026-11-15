from pathlib import Path
import json,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1];O=R/'outputs';W=R/'work';E=O/'visibility-aob-v4-evidence';E.mkdir(exist_ok=True)
common=(W/'sso-visibility-aob-v4.lua').read_text(encoding='utf-8')
def script(selection):
 text='// Update-tolerant AOB visibility patch; future semantic changes still require review.\n// Exact-match count + branch/helper validation + dynamic original-byte restoration.\n// Disable earlier visibility tables first; keep CE open until restoration.\n'
 for mode in ['ENABLE','DISABLE']:
  text+=f'\n[{mode}]\n{{$lua}}\nif syntaxcheck then return end\n'+common+f"\nrun('{mode.lower()}','{selection}')\n"+'{$asm}\n'
 return text
root=ET.Element('CheatTable',{'CheatEngineTableVersion':'45'});entries=ET.SubElement(root,'CheatEntries')
for ident,selection,name in [(1,'avatars','AOB v4: hide other horses + riders'),(2,'pets',"AOB v4: hide other players' pets")]:
 text=script(selection);(O/f'Star-Stable-visibility-AOB-v4-{selection}.cea').write_text(text,encoding='utf-8')
 e=ET.SubElement(entries,'CheatEntry');ET.SubElement(e,'ID').text=str(ident);ET.SubElement(e,'Description').text='"'+name+'"';ET.SubElement(e,'VariableType').text='Auto Assembler Script';ET.SubElement(e,'AssemblerScript').text=text
g=ET.SubElement(entries,'CheatEntry');ET.SubElement(g,'ID').text='10';ET.SubElement(g,'Description').text='"STATUS: resolves while enabled; leave these Byte rows unchecked"';ET.SubElement(g,'GroupHeader').text='1';children=ET.SubElement(g,'CheatEntries')
for ident,name,symbol in [(11,'Rider byte (enabled = 00)','SSOHideAOB4_Rider'),(12,'Horse byte (enabled = 00)','SSOHideAOB4_Horse'),(13,'Pet byte (enabled = 00)','SSOHideAOB4_Pet')]:
 e=ET.SubElement(children,'CheatEntry');ET.SubElement(e,'ID').text=str(ident);ET.SubElement(e,'Description').text='"'+name+'"';ET.SubElement(e,'ShowAsHex').text='1';ET.SubElement(e,'VariableType').text='Byte';ET.SubElement(e,'Address').text=symbol
ET.SubElement(root,'UserdefinedSymbols');ET.indent(root,space='  ');ET.ElementTree(root).write(O/'Star-Stable-visibility-AOB-v4.CT',encoding='utf-8',xml_declaration=True)
(O/'Star-Stable-visibility-AOB-v4-all.cea').write_text(script('all'),encoding='utf-8')
(E/'sso-visibility-aob-v4.lua').write_text(common,encoding='utf-8')
(E/'confirmed-user-outcomes.json').write_text(json.dumps({'v3_horse_rider_visibility':'User confirmed other players and horses disappear while own character/horse remain visible','v3_pet_visibility':'User confirmed other players pets disappear while own pets remain visible','chat_or_network_behaviour_tested':False,'controlled_fps_improvement_measured':False,'v4_live_ce_execution':'User confirmed both AOB entries enable and retain the same behavior; own character/horse/pets stay visible','date':'2026-11-15'},indent=2))
print(json.dumps({'table':'Star-Stable-visibility-AOB-v4.CT','fixed_patch_rvas':False,'hardcoded_original_displacements':False,'separate_toggles':2}))
