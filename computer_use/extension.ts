import { Type } from '@earendil-works/pi-ai';
import { defineTool, type ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
const root = process.env.BUGCRAFT_HARNESS_ROOT!;
const actions=['screenshot','click','move','move_relative','drag','key','type','scroll','wait','pause_vm','resume_vm'];
const fields={
  x:Type.Optional(Type.Integer()),y:Type.Optional(Type.Integer()),to_x:Type.Optional(Type.Integer()),to_y:Type.Optional(Type.Integer()),
  dx:Type.Optional(Type.Integer({minimum:-500,maximum:500})),dy:Type.Optional(Type.Integer({minimum:-500,maximum:500})),
  button:Type.Optional(Type.Integer({minimum:1,maximum:3})),clicks:Type.Optional(Type.Integer({minimum:1,maximum:2})),
  keys:Type.Optional(Type.Array(Type.String(),{maxItems:8})),text:Type.Optional(Type.String({maxLength:2000})),
  duration:Type.Optional(Type.Number({minimum:0,maximum:5})),scroll:Type.Optional(Type.Integer({minimum:-10,maximum:10}))
};
export default function(pi: ExtensionAPI) {
  pi.on('session_start', async (_event, ctx) => {
    const inventory = { lane:Number(process.env.BUGCRAFT_LANE || '0'), lane_config:createHash('sha256').update(readFileSync(resolve(root,'bugcraft_bench/lane.py'))).digest('hex'), tools: pi.getActiveTools(), model: ctx.model?.id, provider: ctx.model?.provider, thinking:pi.getThinkingLevel(),
      extension: createHash('sha256').update(readFileSync(resolve(root,'computer_use/extension.ts'))).digest('hex'),
      helper: createHash('sha256').update(readFileSync(resolve(root,'computer_use/helper.py'))).digest('hex'),
      vm_control: createHash('sha256').update(readFileSync(resolve(root,'computer_use/vm_pause.py'))).digest('hex'), timing_protocol:'explicit-vm-pause-v1',
      skill: createHash('sha256').update(readFileSync(resolve(root,'computer_use/SKILL.md'))).digest('hex'),
      skills: pi.getCommands().filter(c=>c.source==='skill').map(c=>c.name) }; 
    pi.appendEntry('computer-use-inventory', inventory);
    if(process.env.BUGCRAFT_INVENTORY) writeFileSync(process.env.BUGCRAFT_INVENTORY, JSON.stringify(inventory,null,2));
  });
  pi.registerTool(defineTool({
    name:'computer', label:'Computer', description:'View and control the Windows guest desktop. Coordinates are absolute pixels in the returned full-resolution screenshot. Every action returns a new PNG. Keys use VNC names: ctrl, alt, shift, super, enter, esc, tab, backspace, delete, space, f1..f12, up/down/left/right, or a character. Held keys/buttons always release. Maximum hold/wait is five seconds. move_relative(dx,dy) sends relative pointer motion for pointer-locked applications; dx positive is right, dy positive is down, bounded to 500 pixels per axis. Use absolute move/click for ordinary menus. pause_vm freezes the guest VM without opening game menus; resume_vm resumes it. Screenshots still work while paused. Resume before gameplay inputs or wait. Pausing does not stop the 20-minute wall-clock budget. For code-style chaining use action=batch with an ordered actions array (1-16 actions, no nesting, at most 30 seconds of requested input/wait time). Returns the final screenshot and ordered completion log; stops at first failed action.',
    parameters:Type.Object({
      action:Type.Union([...actions,'batch'].map(x=>Type.Literal(x))), ...fields,
      actions:Type.Optional(Type.Array(Type.Object({action:Type.Union(actions.map(x=>Type.Literal(x))),...fields}),{minItems:1,maxItems:16}))
    }),
    async execute(_id, params, signal) {
      const result:any = await new Promise((done,fail)=>{
        const p=spawn(resolve(root,'.venv/bin/python'),[resolve(root,'computer_use/helper.py')],{stdio:['pipe','pipe','pipe']});
        let out='',err=''; let settled=false;
        // Do not interrupt held input: helper finally-release completes before process exit.
        const timer=setTimeout(()=>{p.kill('SIGTERM');fail(new Error('Computer transport timeout; attempt must stop'))},90000);
        p.stdout.on('data',x=>{out+=x;if(out.length>16*1024*1024){p.kill();fail(new Error('Screenshot oversized'))}});
        p.stderr.on('data',x=>{err+=x});p.on('error',e=>{clearTimeout(timer);fail(e)});
        p.on('close',code=>{clearTimeout(timer);if(code!==0)fail(new Error('Computer transport failed: '+err.slice(-1000)));else {try{done(JSON.parse(out))}catch(e){fail(e)}}});
        p.stdin.end(JSON.stringify(params));
      });
      if(process.env.BUGCRAFT_SCREENSHOT_DIR) writeFileSync(resolve(process.env.BUGCRAFT_SCREENSHOT_DIR, `${Date.now()}-${_id.replace(/[^a-zA-Z0-9_-]/g,'_')}.png`),Buffer.from(result.image,'base64'));
      return { content:[{type:'text',text:`Windows desktop ${result.width}x${result.height}. Origin (0,0) top-left. VM state: ${result.vm_state}. Action log: ${JSON.stringify(result.action_log || [])}${result.error ? '. ERROR: '+result.error : ''}`},
        {type:'image',data:result.image,mimeType:'image/png'}], isError:!!result.error, details:{width:result.width,height:result.height,vm_state:result.vm_state,action_log:result.action_log,error:result.error} };
    }
  }));
}
