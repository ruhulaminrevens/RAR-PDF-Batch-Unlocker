"""RAR PDF Batch Unlocker — offline Tkinter desktop GUI (Python 3.10+)."""
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import time
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from core import Settings, process, scan, FAILED, ACTIONS, engine_status, qpdf_version
import diagnostics
from branding import APP_NAME, VERSION, prepare_windows
from ui import ModernUI, STATUS_LABELS, BG, INSET, TEXT, CYAN

HINTS = """Password recovery guidance (not a password bypass):

BANK & CREDIT CARD: Check the original statement email, official bank help pages, statement portal, and issuer support. Password conventions vary by institution and over time. Do not assume a generic DOB/card-number rule.

OFFICE / FINANCIAL: Ask the document author or approved records administrator; search your organization's password manager and approved backup archives. Avoid unauthorized access to employee or client documents.

PERSONAL / GOVERNMENT: Revisit the issuing authority's portal or document-delivery message and its official helpdesk.

OTHER: Check the sender's delivery message, your password manager and the original unencrypted copy.

Only try plausible passwords you are authorized to use. Strong unknown opening passwords may not be recoverable. Never upload confidential documents to unknown PDF unlocking websites. Save unencrypted copies in access-controlled folders; unlocked bank/identity records remain sensitive.
"""

def find_qpdf():
    """Prefer packaged qpdf, then existing user installation."""
    locations = [Path(sys.executable).resolve().parent / 'qpdf' / 'bin' / 'qpdf.exe',
                 Path(sys.executable).resolve().parent / 'qpdf' / 'qpdf.exe',
                 Path(__file__).resolve().parent / 'qpdf' / 'bin' / 'qpdf.exe']
    for candidate in locations:
        if candidate.is_file():
            return str(candidate)
    return shutil.which('qpdf') or ''

class App(ModernUI, tk.Tk):
    def __init__(self):
        prepare_windows()
        super().__init__()
        diagnostics.install(self)
        if os.environ.get('RAR_TK_SCALING'):  # QA: emulate 125/150/200 % display scaling
            self.tk.call('tk','scaling',float(os.environ['RAR_TK_SCALING']))
        self.title(f'{APP_NAME} · {VERSION}')
        scale=max(1.0,float(self.tk.call('tk','scaling'))*72/96)
        width=min(int(1320*scale),self.winfo_screenwidth()-60)
        height=min(int(960*scale),self.winfo_screenheight()-80)
        self.geometry(f'{width}x{height}+20+20');self.minsize(min(900,width),min(560,height))
        self.events=queue.Queue();self.stop_flag=threading.Event();self.worker=None
        self.busy=False;self.closing=False;self.poll_id=None
        self.password_groups={'General':[]};self.passwords=self.password_groups['General']
        self.source=tk.StringVar();self.destination=tk.StringVar()
        self.qpdf=tk.StringVar(value=find_qpdf())
        self.limit=tk.StringVar(value='0');self.max_attempts=tk.StringVar(value='30')
        self.group=tk.StringVar(value='General')
        self.dry_run=tk.BooleanVar();self.analyze_only=tk.BooleanVar()
        self.include_unencrypted=tk.BooleanVar(value=False)
        self.relative_reports=tk.BooleanVar(value=True);self.retry_report=tk.StringVar()
        self.timeout=tk.StringVar(value='60');self.workers=tk.StringVar(value=str(min(4,max(1,(os.cpu_count() or 2)//2))))
        self.html_summary=tk.BooleanVar(value=True);self.continue_mode=tk.StringVar(value='retry')
        self.extra_files=[];self.files_summary=tk.StringVar(value='None added — use a source folder, add PDFs, or both')
        self.engine_text=tk.StringVar(value='Checking engine…');self.last_html=''
        self.status=tk.StringVar(value='Ready when you are. Choose your folders to begin.')
        self.progress=tk.DoubleVar(value=0);self.progress_text=tk.StringVar(value='0 / 0')
        self.timing=tk.StringVar(value='Elapsed —   •   Estimated remaining —')
        self.mode_summary=tk.StringVar();self.pw_count=tk.StringVar(value='0 passwords in General (values hidden)')
        self.show_password=tk.BooleanVar();self.search=tk.StringVar()
        self.result_detail=tk.StringVar(value='Select a result to see its details.')
        self.report_text=tk.StringVar(value='No report yet.')
        self.filter_status=tk.StringVar(value='All statuses')
        self.counts={};self.last_report='';self.last_output='';self.row_items=[];self.result_records={}
        self.total=0;self.completed=0;self.started_at=None;self.active_source=None
        self._build();self.poll_id=self.after(100,self._poll)
        threading.Thread(target=self._check_engine,daemon=True).start()
        self.protocol('WM_DELETE_WINDOW',self._close)

    def _check_engine(self):
        qpdf=self.qpdf.get()
        if not qpdf:
            self.events.put(('engine','qpdf was not found. Select qpdf.exe below.'));return
        ok,detail=engine_status(qpdf)
        state={True:'Integrity verified',False:'WARNING: integrity check failed',None:'External engine'}[ok]
        self.events.put(('engine',f'{qpdf_version(qpdf)} · {state} — {detail}'))

    def _add_files(self):
        if self.busy:return
        chosen=filedialog.askopenfilenames(title='Add PDF files',filetypes=[('PDF files','*.pdf'),('All files','*')])
        added=0
        known={os.path.normcase(os.path.abspath(f)) for f in self.extra_files}
        for f in chosen:
            key=os.path.normcase(os.path.abspath(f))
            if key not in known:self.extra_files.append(f);known.add(key);added+=1
        self._files_changed(len(chosen)-added)

    def _clear_files(self):
        self.extra_files.clear();self._files_changed(0)

    def _files_changed(self,duplicates=0):
        n=len(self.extra_files)
        if not n:self.files_summary.set('None added — use a source folder, add PDFs, or both')
        else:
            names=', '.join(Path(f).name for f in self.extra_files[:3])+(' …' if n>3 else '')
            self.files_summary.set(f'{n} PDF{"s" if n!=1 else ""}: {names}'+(f'  ({duplicates} duplicate ignored)' if duplicates else ''))

    def _delete_group(self):
        name=self.group.get()
        if self.busy or name=='General':
            messagebox.showinfo('Delete group','The General group cannot be deleted.');return
        if not messagebox.askyesno('Delete group',f'Delete the group “{name}” and its session passwords?\nFolder rules that use it must be removed too.'):return
        self.password_groups.pop(name,None)
        self.groupbox.config(values=list(self.password_groups));self.group.set('General');self._update_count()

    def _open_html(self):self._open_path(self.last_html)

    def _sort_table(self,table,key):
        cols=list(table['columns']);i=cols.index(key)
        reverse=getattr(self,'_sort_state',(None,False))==(key,False)
        self._sort_state=(key,reverse)
        def value(item):
            v=table.set(item,key)
            try:return (0,float(v))
            except ValueError:return (1,str(v).casefold())
        items=sorted(table.get_children(''),key=value,reverse=reverse)
        for n,item in enumerate(items):table.move(item,'',n)
        for k in cols:
            text=table.heading(k,'text').rstrip(' ▲▼')
            table.heading(k,text=text+((' ▼' if reverse else ' ▲') if k==key else ''))

    def _use_last_report(self):
        if self.last_report:
            self.retry_report.set(self.last_report)
            messagebox.showinfo('Retry enabled','Next run will process failed records from the previous report only.')
        else:messagebox.showinfo('No report','Complete a batch first or choose an existing CSV.')
    def _filter_rows(self):
        if not hasattr(self,'table'):return
        selected=self.filter_status.get();query=self.search.get().casefold().strip()
        for item in self.table.get_children():self.table.detach(item)
        for item,values in self.row_items:
            if (selected=='All statuses' or values[0]==selected or (selected=='Needs attention' and values[0] in FAILED)) and (not query or query in ' '.join(map(str,values)).casefold()):
                self.table.move(item,'','end')

    def _select_result(self,table):
        selected=table.selection()
        if selected:
            r=self.result_records.get(selected[0],{})
            lines=[f"{STATUS_LABELS.get(r.get('status',''),r.get('status',''))} — {ACTIONS.get(r.get('status',''),'')}"]
            if r.get('details'):lines.append('Details: '+r['details'])
            if r.get('warnings'):lines.append('Notes: '+r['warnings'])
            lines.append('Source: '+r.get('source',''))
            if r.get('output') and r.get('status') in ('Unlocked','CopiedUnencrypted'):lines.append('Output: '+r['output'])
            self.result_detail.set('\n'.join(lines))

    def _open_path(self,path):
        if not path or not Path(path).exists():
            messagebox.showinfo('Not available','Complete a run first, or check that the file or folder still exists.');return
        try:
            if sys.platform=='win32':os.startfile(str(Path(path).resolve()))
            else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(Path(path).resolve())])
        except OSError as exc:messagebox.showerror('Could not open',str(exc))

    def _open_report(self):self._open_path(self.last_report)
    def _open_output(self):self._open_path(self.last_output or self.destination.get())

    # ---- PDF tools ---------------------------------------------------------
    def _tool_pick_file(self,var):
        v=filedialog.askopenfilename(filetypes=[('PDF files','*.pdf'),('All files','*')])
        if v:var.set(v)

    def _tool_add(self,box,kind):
        if self.busy:return
        if kind=='img':
            types=[('Images','*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp'),('All files','*')]
        else:
            types=[('PDF files','*.pdf'),('All files','*')]
        chosen=filedialog.askopenfilenames(title='Add files',filetypes=types)
        known={os.path.normcase(os.path.abspath(p)) for p in box._paths}
        for f in chosen:
            key=os.path.normcase(os.path.abspath(f))
            if key not in known:
                box._paths.append(f);known.add(key);box.insert('end',os.path.basename(f))

    def _tool_remove(self,box):
        if self.busy:return
        for i in reversed(box.curselection()):
            del box._paths[i];box.delete(i)

    def _tool_clear(self,box):
        if self.busy:return
        box._paths.clear();box.delete(0,'end')

    def _tool_move(self,box,delta):
        if self.busy:return
        sel=box.curselection()
        if not sel:return
        i=sel[0];j=i+delta
        if not 0<=j<len(box._paths):return
        box._paths[i],box._paths[j]=box._paths[j],box._paths[i]
        name_i=box.get(i);box.delete(i);box.insert(j,name_i)
        box.selection_clear(0,'end');box.selection_set(j);box.activate(j)

    def _ask_output_file(self,default,types):
        v=filedialog.asksaveasfilename(defaultextension=types[0][1].split('*')[-1],initialfile=default,filetypes=types)
        return Path(v) if v else None

    def _ask_output_dir(self):
        v=filedialog.askdirectory(title='Choose an output folder')
        return Path(v) if v else None

    def _run_tool(self,make_call,open_target):
        """make_call(password) -> toolkit.Result. Retries once with a prompted password
        if the input turns out to be protected."""
        if self.busy:return
        self._set_busy(True);self.stop_btn.configure(state='disabled');self.tool_status.set('Working…')
        def work():
            import toolkit
            try:
                try:
                    result=make_call(None)
                except toolkit.PasswordNeeded:
                    self.events.put(('tool_need_pw',{'make_call':make_call,'open':open_target}));return
                self.events.put(('tool_done',{'result':result,'open':open_target}))
            except toolkit.ToolkitError as exc:
                self.events.put(('tool_error',str(exc)))
            except Exception as exc:
                import diagnostics;diagnostics.log_exception(type(exc),exc,exc.__traceback__,'pdf-tool')
                self.events.put(('tool_error',f'Unexpected error: {type(exc).__name__}'))
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()

    def _tool_merge(self):
        box=self.merge_list
        if len(box._paths)<2:
            messagebox.showinfo('Merge PDFs','Add at least two PDFs to merge.');return
        out=self._ask_output_file('merged.pdf',[('PDF','*.pdf')])
        if not out:return
        import toolkit
        self._run_tool(lambda pw:toolkit.merge_pdfs([Path(p) for p in box._paths],out),out.parent)

    def _tool_split(self,mode):
        src=self.split_input.get().strip()
        if not src:
            messagebox.showinfo('Split & organize','Choose a source PDF first.');return
        import toolkit
        rotate=int(self.split_rotate.get())
        if mode=='each':
            out=self._ask_output_dir()
            if not out:return
            self._run_tool(lambda pw:toolkit.split_pdf(Path(src),out,password=pw),out)
        else:
            spec=self.split_pages.get().strip()
            if not spec:
                messagebox.showinfo('Export selected pages','Enter page numbers, e.g. 1,3-5.');return
            out=self._ask_output_file(Path(src).stem+'-pages.pdf',[('PDF','*.pdf')])
            if not out:return
            def call(pw):
                n=toolkit.page_count(Path(src),pw)
                keep=toolkit.parse_page_spec(spec,n)
                rot={p:rotate for p in keep} if rotate else None
                return toolkit.organize_pdf(Path(src),out,keep=keep,rotations=rot,password=pw)
            self._run_tool(call,out.parent)

    def _tool_img2pdf(self):
        box=self.img_list
        if not box._paths:
            messagebox.showinfo('Images → PDF','Add at least one image.');return
        out=self._ask_output_file('images.pdf',[('PDF','*.pdf')])
        if not out:return
        import toolkit
        self._run_tool(lambda pw:toolkit.images_to_pdf([Path(p) for p in box._paths],out),out.parent)

    def _tool_pdf2img(self):
        src=self.rimg_input.get().strip()
        if not src:
            messagebox.showinfo('PDF → images','Choose a source PDF first.');return
        out=self._ask_output_dir()
        if not out:return
        import toolkit
        fmt=self.rimg_fmt.get();dpi=int(self.rimg_dpi.get())
        self._run_tool(lambda pw:toolkit.pdf_to_images(Path(src),out,fmt=fmt,dpi=dpi,password=pw),out)

    def _tool_convert(self,kind):
        src=self.conv_input.get().strip()
        if not src:
            messagebox.showinfo('Convert','Choose a source PDF first.');return
        ext='.'+kind
        out=self._ask_output_file(Path(src).stem+ext,[(kind.upper(),'*'+ext)])
        if not out:return
        import toolkit
        fn=toolkit.pdf_to_docx if kind=='docx' else toolkit.pdf_to_xlsx
        self._run_tool(lambda pw:fn(Path(src),out,password=pw),out.parent)

    def _browse(self,var,folder):
        v=filedialog.askdirectory() if folder else filedialog.askopenfilename(filetypes=[('Executable','*.exe'),('All files','*')])
        if v:var.set(v)
    def _select_report(self):
        v=filedialog.askopenfilename(filetypes=[('CSV reports','*.csv')]);
        if v:self.retry_report.set(v)
    def _new_group(self):
        name=simpledialog.askstring('New group','Enter a label (e.g. Bank or Office):',parent=self)
        if name and any(c in name for c in '=\r\n'):
            messagebox.showerror('Invalid group','Group names cannot contain = or line breaks.');return
        if name and name.strip() and name.strip() not in self.password_groups:
            name=name.strip();self.password_groups[name]=[]
            self.groupbox.config(values=list(self.password_groups));self.group.set(name);self._update_count()
    def _update_count(self):
        self.pw_count.set(f'{len(self.password_groups.get(self.group.get(),[]))} passwords in {self.group.get()} (values hidden)')
        self.session_summary.set(f'{sum(len(v) for v in self.password_groups.values())} session passwords')
    def _add_password(self):
        pw=self.pw_entry.get();self.pw_entry.delete(0,'end')
        if self.busy or not pw:return
        if '\r' in pw or '\n' in pw:messagebox.showerror('Invalid','Password contains a newline');return
        arr=self.password_groups.setdefault(self.group.get(),[])
        diagnostics.remember_secret(pw)
        if pw in arr:self.status.set('That password is already in this group; duplicate ignored.')
        else:arr.append(pw)
        self._update_count()
    def _clear(self):
        self.password_groups[self.group.get()].clear();self.pw_entry.delete(0,'end');self._update_count()
    def _vault_name(self):
        return simpledialog.askstring('Windows Credential Locker','Vault entry name (not password):',parent=self)
    def _save_vault(self):
        name=self._vault_name();pw=self.pw_entry.get()
        if not name:return
        try:
            import vault
            vault.save(name,pw)
            self.pw_entry.delete(0,'end')
            messagebox.showinfo('Saved','Password stored in your Windows Credential Locker.')
        except Exception as e:messagebox.showerror('Vault',str(e))
    def _load_vault(self):
        name=self._vault_name()
        if not name:return
        try:
            import vault
            value=vault.load(name)
            if value:
                diagnostics.remember_secret(value)
                arr=self.password_groups.setdefault(self.group.get(),[])
                if value not in arr:arr.append(value)
                self._update_count();messagebox.showinfo('Loaded','Password loaded into current session group.')
            else:messagebox.showinfo('Not found','No stored credential with this name.')
        except Exception as e:messagebox.showerror('Vault',str(e))
    def _delete_vault(self):
        name=self._vault_name()
        if not name:return
        if not messagebox.askyesno('Delete stored credential','Permanently remove this entry from Windows Credential Locker?'):return
        try:
            import vault
            vault.delete(name);messagebox.showinfo('Deleted','Vault entry deleted.')
        except Exception as e:messagebox.showerror('Vault',str(e))
    def _hints(self):
        win=tk.Toplevel(self);win.title('Official recovery guidance');win.geometry('680x500')
        txt=tk.Text(win,wrap='word',padx=20,pady=20,bg=INSET,fg=TEXT,insertbackground=CYAN,font=('Segoe UI',11));txt.pack(fill='both',expand=True)
        txt.insert('1.0',HINTS);txt.configure(state='disabled')
    def _settings(self,analyze=False):
        try:
            limit=int(self.limit.get());attempts=int(self.max_attempts.get())
        except ValueError:raise ValueError('File limit and maximum attempts must be whole numbers.')
        mapping={}
        for line in self.mapping.get('1.0','end').splitlines():
            if not line.strip():continue
            if '=' not in line:raise ValueError('Mapping requires folder=Group Name per line.')
            folder,group=line.split('=',1);folder=folder.strip();group=group.strip()
            if not folder or group not in self.password_groups or folder.startswith(('/', '\\')) or '..' in Path(folder.replace('\\','/')).parts:
                raise ValueError('Invalid mapping or unknown group: '+line)
            mapping[folder]=group
        if not (self.source.get().strip() or self.extra_files):raise ValueError('Choose a source folder or add PDF files.')
        if not self.destination.get().strip():raise ValueError('Choose an output folder.')
        try:timeout=int(self.timeout.get());workers=int(self.workers.get())
        except ValueError:raise ValueError('Timeout and parallel workers must be whole numbers.')
        report=self.retry_report.get().strip();resume=self.continue_mode.get()=='resume'
        return Settings(Path(self.source.get().strip()) if self.source.get().strip() else None,Path(self.destination.get()),self.qpdf.get() or 'qpdf',
                        list(self.password_groups['General']),limit,self.dry_run.get(),
                        analyze_only=analyze,failed_report='' if resume else report,resume_report=report if resume else '',
                        timeout=timeout,workers=workers,html_summary=self.html_summary.get(),app_version=VERSION,
                        inputs=[Path(f) for f in self.extra_files],
                        password_groups={k:list(v) for k,v in self.password_groups.items() if k!='General'},
                        folder_groups=mapping,max_attempts=attempts,
                        relative_reports=self.relative_reports.get(),include_unencrypted=self.include_unencrypted.get())
    def _scan(self):self._prepare('scan')
    def _start(self,analyze):self._prepare('analyze' if analyze else 'unlock')

    def _set_busy(self,value):
        self.busy=value
        for widget,normal in self.mutables:widget.configure(state='disabled' if value else normal)
        self.stop_btn.configure(state='normal' if value else 'disabled')
        if value:
            self.show_password.set(False);self.pw_entry.configure(show='●')

    def _prepare(self,mode):
        if self.busy:return
        try:settings=self._settings(mode=='analyze')
        except Exception as exc:messagebox.showerror('Configuration error',str(exc));return
        self.stop_flag=threading.Event();self._set_busy(True)
        self.status.set('Scanning folders…');self.started_at=None
        self.worker=threading.Thread(target=self._scan_work,args=(settings,mode),daemon=True);self.worker.start()

    def _scan_work(self,settings,mode):
        try:
            plan=scan(settings)
            try:free=shutil.disk_usage(next(p for p in [settings.destination,*settings.destination.parents] if p.exists())).free
            except (OSError,StopIteration):free=None
            self.events.put(('prepared',{'settings':settings,'mode':mode,'source':plan.base,'count':len(plan.files),'plan':plan,'free':free}))
        except Exception as exc:self.events.put(('error',str(exc)))

    def _prepared(self,payload):
        if self.closing:return
        if self.stop_flag.is_set():
            self._done();self.status.set('Scan cancelled. No files changed.');return
        settings=payload['settings'];count=payload['count']
        self.total=count;self.metric_vars['total'].set(str(count))
        if payload['mode']=='scan':
            plan=payload['plan']
            self._done();self.status.set(f"{count} PDFs found ({plan.total_bytes/1048576:.1f} MB) · {plan.duplicates} duplicates ignored · {len(plan.rejected)} not included · {plan.existing_outputs} outputs already exist. No files modified.");return
        if not count:
            self._done();self.status.set('No matching PDF files found. Check your folders, limit or retry report.');return
        if payload['mode']!='scan' and not (settings.analyze_only or settings.dry_run) and not messagebox.askyesno('Confirm batch',self._preview_text(payload),parent=self):
            self._done();self.status.set('Batch not started.');return
        for item,_ in self.row_items:self.table.delete(item)
        for item in self.preview_table.get_children():self.preview_table.delete(item)
        self.counts={};self.row_items=[];self.result_records={};self.completed=0
        self.last_report='';self.last_output=str(settings.destination.resolve());self.report_text.set('Report will be available when this run finishes.' if not settings.dry_run else 'Dry run does not create a report.')
        self.filter_status.set('All statuses');self.search.set('');self.result_detail.set('Select a result to see its details.')
        self.progress.set(0);self.progress_text.set(f'0 / {count}')
        self.active_source=payload['source'];self.started_at=time.monotonic()
        self.status.set('Processing…');self._update_metrics()
        self.worker=threading.Thread(target=self._work,args=(settings,),daemon=True);self.worker.start()

    def _preview_text(self,payload):
        plan=payload['plan'];s=payload['settings'];free=payload['free']
        groups=sum(1 for v in s.password_groups.values() if v)+(1 if s.passwords else 0)
        pw=len(s.passwords)+sum(len(v) for v in s.password_groups.values())
        lines=[f"Process {len(plan.files)} PDFs ({plan.total_bytes/1048576:.1f} MB)?",'',
               f"• Duplicates ignored: {plan.duplicates}",f"• Not included (links, unsupported, name conflicts): {len(plan.rejected)}",
               f"• Outputs that already exist and will be skipped: {plan.existing_outputs}",
               f"• Passwords: {pw} in {groups} active group(s) · up to {s.max_attempts} attempts per PDF",
               f"• Timeout {s.timeout} s · {s.workers} parallel worker(s)"+(' · resume' if s.resume_report else ' · failed-only retry' if s.failed_report else '')]
        if free is not None:
            lines.append(f"• Free space on output drive: {free/1073741824:.1f} GB"+('  ⚠ may be too little' if free<plan.total_bytes*2 else ''))
        lines+=['','Originals stay unchanged. Existing outputs are never overwritten.']
        return '\n'.join(lines)

    def _work(self,settings):
        try:process(settings,lambda kind,p:self.events.put((kind,p)),self.stop_flag)
        except Exception as exc:self.events.put(('error',str(exc)))

    def _stop(self):
        self.stop_flag.set();self.stop_btn.configure(state='disabled')
        self.status.set('Stopping safely after the current scan or qpdf attempt…')

    def _result(self,p):
        self.completed=p['index'];self.total=p['total']
        self.progress.set(100*self.completed/self.total if self.total else 0)
        self.progress_text.set(f"{self.completed} / {self.total}   ·   {self.progress.get():.0f}%")
        self.counts[p['status']]=self.counts.get(p['status'],0)+1
        name=p.get('relative') or os.path.relpath(p['source'],self.active_source)
        values=(p['status'],name,p.get('security',''),p.get('group',''),p['attempts'],p['elapsed_seconds'])
        item=f'r{len(self.row_items)}'
        tag='good' if p['status'] in ('Unlocked','CopiedUnencrypted') else 'error' if p['status'] in FAILED else 'warn' if p['status']=='PasswordRequired' else 'skip' if p['status'].startswith('Skipped') else 'neutral'
        tags=(tag,'odd') if len(self.row_items)%2 else (tag,)
        shown=(STATUS_LABELS.get(p['status'],p['status']),*values[1:])
        self.table.insert('','end',iid=item,values=shown,tags=tags);self.row_items.append((item,values));self.result_records[item]=p
        query=self.search.get().casefold().strip()
        if self.filter_status.get() not in ('All statuses',p['status']) or (query and query not in ' '.join(map(str,values)).casefold()):self.table.detach(item)
        self.preview_table.insert('','end',iid=item,values=(shown[0],name),tags=tags)
        if len(self.preview_table.get_children())>4:self.preview_table.delete(self.preview_table.get_children()[0])
        self.status.set(f"{'Stopping' if self.stop_flag.is_set() else 'Processing'} · {self.completed} of {self.total} PDFs")
        self._update_metrics()

    def _update_metrics(self):
        self.metric_vars['total'].set(str(self.total))
        self.metric_vars['unlocked'].set(str(self.counts.get('Unlocked',0)))
        self.metric_vars['attention'].set(str(sum(v for k,v in self.counts.items() if k in FAILED)))
        self.metric_vars['skipped'].set(str(sum(v for k,v in self.counts.items() if k.startswith('Skipped') or k=='DryRun')))

    @staticmethod
    def _duration(seconds):
        value=max(0,int(seconds));return f'{value//60:02d}:{value%60:02d}'

    def _update_timing(self):
        if self.started_at is None:return
        elapsed=time.monotonic()-self.started_at
        eta=(elapsed/self.completed*(self.total-self.completed)) if self.completed else None
        remaining=self._duration(eta) if eta is not None else '—'
        rate=f"   •   {self.completed/elapsed*60:.0f} PDFs/min" if self.completed and elapsed>1 else ''
        self.timing.set(f"Elapsed {self._duration(elapsed)}   •   Estimated remaining {remaining}{rate}" if self.busy else f'Elapsed {self._duration(elapsed)}{rate}')

    def _poll(self):
        try:
            # Bound UI work per tick so Stop and navigation remain responsive.
            for _ in range(100):
                kind,p=self.events.get_nowait()
                if self.closing:continue
                if kind=='prepared':self._prepared(p)
                elif kind=='scan':self.total=p['count'];self.metric_vars['total'].set(str(self.total))
                elif kind=='result':self._result(p)
                elif kind=='engine':self.engine_text.set(p)
                elif kind=='done':
                    self._done();self.last_report=p['report'] or '';self.last_html=p.get('html') or ''
                    self.report_text.set(f"CSV: {self.last_report}"+(f"\nHTML summary: {self.last_html}" if self.last_html else '') if self.last_report else 'No report created (dry run).')
                    state='Stopped: output drive is full' if p.get('halted')=='DiskFull' else 'Stopped safely' if p['cancelled'] else 'Complete'
                    elapsed=(p.get('summary') or {}).get('elapsed_seconds')
                    self.status.set(f"{state} · {self.completed} of {self.total} PDFs"+(f" · {elapsed:.1f} s" if elapsed else ''))
                elif kind=='error':
                    self._done();self.status.set('Processing could not finish. Review the error and your settings.')
                    diagnostics.log_event('Run error shown to user')
                    messagebox.showerror('Processing error',p)
                elif kind=='tool_done':
                    self._done();r=p['result']
                    outs=r.outputs;where=outs[0].parent if outs else p['open']
                    self.tool_status.set(f'Done — {r.note}. Saved to: {where}')
                    if messagebox.askyesno('Finished',f'{r.note}.\n\nOpen the output folder?'):self._open_path(str(p['open']))
                elif kind=='tool_need_pw':
                    pw=simpledialog.askstring('Protected PDF','This PDF needs its open password:',show='●',parent=self)
                    if not pw:
                        self._done();self.tool_status.set('Cancelled — the PDF is password-protected.')
                    else:
                        diagnostics.remember_secret(pw)
                        make=p['make_call'];target=p['open']
                        def work():
                            import toolkit
                            try:self.events.put(('tool_done',{'result':make(pw),'open':target}))
                            except toolkit.ToolkitError as exc:self.events.put(('tool_error',str(exc)))
                            except Exception as exc:
                                diagnostics.log_exception(type(exc),exc,exc.__traceback__,'pdf-tool');self.events.put(('tool_error',f'Unexpected error: {type(exc).__name__}'))
                        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
                elif kind=='tool_error':
                    self._done();self.tool_status.set('Could not finish: '+p);messagebox.showerror('PDF tools',p)
        except queue.Empty:pass
        if self.busy:self._update_timing()
        self.poll_id=self.after(100,self._poll)

    def _done(self):
        self._set_busy(False);self._update_timing();self.started_at=None

    def _close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno('Processing','Stop and wait for current attempt?'):return
            self.closing=True;self.stop_flag.set();self.after(200,self._wait_close)
        else:self._shutdown()
    def _wait_close(self):
        if self.worker and self.worker.is_alive():self.after(200,self._wait_close)
        else:self._shutdown()
    def _shutdown(self):
        for passwords in self.password_groups.values():passwords.clear()
        diagnostics.forget_secrets()
        if self.poll_id:self.after_cancel(self.poll_id)
        self.pw_entry.delete(0,'end');self.destroy()

if __name__=='__main__':App().mainloop()
