"""RAR PDF Batch Unlocker — offline Tkinter desktop GUI (Python 3.10+)."""
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from core import Settings, process, scan, FAILED

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

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('RAR PDF Batch Unlocker · Security & Recovery')
        self.geometry('1180x900'); self.minsize(980, 700)
        self.events = queue.Queue(); self.stop_flag = threading.Event(); self.worker = None
        self.password_groups = {'General': []}; self.passwords = self.password_groups['General']
        self.source = tk.StringVar(); self.destination = tk.StringVar()
        self.qpdf = tk.StringVar(value=find_qpdf())
        self.limit = tk.StringVar(value='0'); self.max_attempts=tk.StringVar(value='30')
        self.group = tk.StringVar(value='General')
        self.dry_run = tk.BooleanVar(); self.analyze_only=tk.BooleanVar()
        self.include_unencrypted=tk.BooleanVar(value=False)
        self.relative_reports=tk.BooleanVar(value=True)
        self.retry_report=tk.StringVar()
        self.status=tk.StringVar(value='Ready. Select folders and click Analyze or Start.')
        self.counts={}; self.last_report=''
        self.filter_status=tk.StringVar(value='All statuses')
        self._build(); self.after(120,self._poll)
        self.protocol('WM_DELETE_WINDOW',self._close)

    def _build(self):
        style=ttk.Style(self)
        if 'clam' in style.theme_names(): style.theme_use('clam')
        self.configure(background='#f3f6fa')
        style.configure('.',font=('Segoe UI',10), background='#f3f6fa',foreground='#20324b')
        style.configure('TFrame',background='#f3f6fa')
        style.configure('TLabel',background='#f3f6fa',foreground='#20324b')
        style.configure('Title.TLabel',font=('Segoe UI',23,'bold'),foreground='#172f50')
        style.configure('TLabelframe',background='#f3f6fa',bordercolor='#d9e2ed',relief='solid')
        style.configure('TLabelframe.Label',font=('Segoe UI',11,'bold'),background='#f3f6fa',foreground='#24466f')
        style.configure('TButton',font=('Segoe UI',10,'bold'),padding=(12,8),background='#e4edf8')
        style.map('TButton',background=[('active','#d3e2f5')])
        style.configure('Primary.TButton',background='#1766b1',foreground='#ffffff',padding=(14,9))
        style.map('Primary.TButton',background=[('active','#11508d'),('disabled','#8aa2bb')],foreground=[('disabled','#eeeeee')])
        style.configure('TEntry',padding=6,fieldbackground='#ffffff')
        style.configure('TCombobox',padding=5)
        style.configure('Treeview',font=('Segoe UI',10),rowheight=28,background='#ffffff',fieldbackground='#ffffff')
        style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),background='#dbe8f6',foreground='#1a3859')
        style.configure('TProgressbar',thickness=14)
        base=ttk.Frame(self,padding=13); base.pack(fill='both',expand=True)
        ttk.Label(base,text='RAR PDF Batch Unlocker',style='Title.TLabel').pack(anchor='w')
        ttk.Label(base,text='SECURE OFFLINE WORKSPACE   •   Local PDF analysis   •   Safe batch unlocking   •   Privacy-first reports').pack(anchor='w',pady=(0,12))
        paths=ttk.LabelFrame(base,text='1   Folders and qpdf',padding=8); paths.pack(fill='x')
        for label,var,is_folder in [('Source',self.source,True),('Output',self.destination,True),('qpdf.exe',self.qpdf,False)]:
            line=ttk.Frame(paths); line.pack(fill='x',pady=2)
            ttk.Label(line,text=label,width=13).pack(side='left')
            ttk.Entry(line,textvariable=var).pack(side='left',fill='x',expand=True,padx=5)
            ttk.Button(line,text='Browse',command=lambda v=var,f=is_folder:self._browse(v,f)).pack(side='left')
        cred=ttk.LabelFrame(base,text='2   Password groups (session-only unless saved to Windows vault)',padding=8)
        cred.pack(fill='x',pady=8)
        top=ttk.Frame(cred);top.pack(fill='x')
        ttk.Label(top,text='Group').pack(side='left')
        self.groupbox=ttk.Combobox(top,textvariable=self.group,values=['General'],width=21,state='readonly')
        self.groupbox.pack(side='left',padx=6)
        ttk.Button(top,text='New group',command=self._new_group).pack(side='left')
        self.pw_entry=ttk.Entry(top,show='●'); self.pw_entry.pack(side='left',fill='x',expand=True,padx=8)
        self.pw_entry.bind('<Return>',lambda e:self._add_password())
        ttk.Button(top,text='Add password',command=self._add_password).pack(side='left')
        ttk.Button(top,text='Clear group',command=self._clear).pack(side='left',padx=5)
        self.pw_count=tk.StringVar(value='0 passwords in General')
        ttk.Label(cred,textvariable=self.pw_count).pack(anchor='w',pady=3)
        vault=ttk.Frame(cred); vault.pack(fill='x')
        ttk.Button(vault,text='Save entered password to Windows vault',command=self._save_vault).pack(side='left')
        ttk.Button(vault,text='Load saved password',command=self._load_vault).pack(side='left',padx=5)
        ttk.Button(vault,text='Delete saved password',command=self._delete_vault).pack(side='left')
        ttk.Label(cred,text='Folder-to-group mapping (one per line: relative/folder=Group Name). General passwords are always tried.').pack(anchor='w',pady=(6,1))
        self.mapping=tk.Text(cred,height=3,wrap='none'); self.mapping.pack(fill='x')
        cfg=ttk.LabelFrame(base,text='3   Mode and limits',padding=8);cfg.pack(fill='x')
        line=ttk.Frame(cfg);line.pack(fill='x')
        ttk.Label(line,text='File limit (0=all)').pack(side='left')
        ttk.Entry(line,textvariable=self.limit,width=7).pack(side='left',padx=5)
        ttk.Label(line,text='Max password attempts per PDF').pack(side='left',padx=(12,0))
        ttk.Entry(line,textvariable=self.max_attempts,width=6).pack(side='left',padx=5)
        ttk.Checkbutton(line,text='Dry run',variable=self.dry_run).pack(side='left',padx=7)
        ttk.Checkbutton(line,text='Copy unencrypted',variable=self.include_unencrypted).pack(side='left')
        line2=ttk.Frame(cfg);line2.pack(fill='x',pady=(6,0))
        ttk.Checkbutton(line2,text='Use relative file paths in reports',variable=self.relative_reports).pack(side='left')
        ttk.Label(line2,text='Retry from previous CSV:').pack(side='left',padx=(15,3))
        ttk.Entry(line2,textvariable=self.retry_report).pack(side='left',fill='x',expand=True)
        ttk.Button(line2,text='Choose CSV',command=self._select_report).pack(side='left',padx=3)
        ttk.Button(line2,text='Clear',command=lambda:self.retry_report.set('')).pack(side='left')
        actions=ttk.Frame(base);actions.pack(fill='x',pady=7)
        ttk.Button(actions,text='Recovery guidance',command=self._hints).pack(side='left')
        self.scan_btn=ttk.Button(actions,text='Scan filenames',command=self._scan);self.scan_btn.pack(side='right')
        self.analyze_btn=ttk.Button(actions,text='Analyze security',command=lambda:self._start(True));self.analyze_btn.pack(side='right',padx=5)
        self.start_btn=ttk.Button(actions,text='Unlock batch',style='Primary.TButton',command=lambda:self._start(False));self.start_btn.pack(side='right')
        self.stop_btn=ttk.Button(actions,text='Stop safely',command=self._stop,state='disabled');self.stop_btn.pack(side='right',padx=5)
        results=ttk.LabelFrame(base,text='4   Progress and results',padding=7);results.pack(fill='both',expand=True)
        self.bar=ttk.Progressbar(results,mode='determinate');self.bar.pack(fill='x',pady=(4,6))
        ttk.Label(results,textvariable=self.status,wraplength=980).pack(anchor='w',pady=5)
        filterline=ttk.Frame(results);filterline.pack(fill='x',pady=(0,4))
        ttk.Label(filterline,text='Filter results:').pack(side='left')
        self.filterbox=ttk.Combobox(filterline,textvariable=self.filter_status,values=['All statuses','Unlocked','PasswordNotMatched','PasswordRequired','PermissionRestricted','Unencrypted','SkippedExisting','Error','Timeout','InvalidPDF'],state='readonly',width=23)
        self.filterbox.pack(side='left',padx=5);self.filterbox.bind('<<ComboboxSelected>>',lambda e:self._filter_rows())
        ttk.Button(filterline,text='Retry failures from last report',command=self._use_last_report).pack(side='right')
        cols=('status','security','group','filename','attempts','seconds')
        self.table=ttk.Treeview(results,columns=cols,show='headings',height=10)
        for key,width in [('status',160),('security',150),('group',115),('filename',400),('attempts',65),('seconds',75)]:
            self.table.heading(key,text=key.title());self.table.column(key,width=width,stretch=(key=='filename'))
        scroll=ttk.Scrollbar(results,orient='vertical',command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set);self.table.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        ttk.Label(base,text='Reports saved to output folder. Never publish unlocked personal documents. Digitally signed PDFs can lose signature validity.').pack(anchor='w',pady=(5,0))

    def _use_last_report(self):
        if self.last_report:
            self.retry_report.set(self.last_report)
            messagebox.showinfo('Retry enabled','Next run will process failed records from the previous report only.')
        else:messagebox.showinfo('No report','Complete a batch first or choose an existing CSV.')
    def _filter_rows(self):
        selected=self.filter_status.get()
        for item in self.table.get_children():
            self.table.detach(item)
        # Reattach only matching rows in recorded order.
        for item,values in getattr(self,'row_items',[]):
            if selected=='All statuses' or values[0]==selected:
                self.table.move(item,'','end')
    def _browse(self,var,folder):
        v=filedialog.askdirectory() if folder else filedialog.askopenfilename(filetypes=[('Executable','*.exe'),('All files','*')])
        if v:var.set(v)
    def _select_report(self):
        v=filedialog.askopenfilename(filetypes=[('CSV reports','*.csv')]);
        if v:self.retry_report.set(v)
    def _new_group(self):
        name=simpledialog.askstring('New group','Enter a label (e.g. Bank / Office):',parent=self)
        if name and name.strip() and name.strip() not in self.password_groups:
            name=name.strip();self.password_groups[name]=[]
            self.groupbox.config(values=list(self.password_groups));self.group.set(name);self._update_count()
    def _update_count(self):
        self.pw_count.set(f'{len(self.password_groups.get(self.group.get(),[]))} passwords in {self.group.get()} (values hidden)')
    def _add_password(self):
        pw=self.pw_entry.get();self.pw_entry.delete(0,'end')
        if not pw:return
        if '\r' in pw or '\n' in pw:messagebox.showerror('Invalid','Password contains a newline');return
        arr=self.password_groups.setdefault(self.group.get(),[])
        if pw not in arr:arr.append(pw)
        self._update_count()
    def _clear(self):
        self.password_groups[self.group.get()]=[];self.pw_entry.delete(0,'end');self._update_count()
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
        txt=tk.Text(win,wrap='word',padx=15,pady=15);txt.pack(fill='both',expand=True)
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
        if not self.source.get() or not self.destination.get():raise ValueError('Choose source and output folders.')
        return Settings(Path(self.source.get()),Path(self.destination.get()),self.qpdf.get() or 'qpdf',
                        list(self.password_groups['General']),limit,self.dry_run.get(),
                        analyze_only=analyze,failed_report=self.retry_report.get().strip(),
                        password_groups={k:list(v) for k,v in self.password_groups.items() if k!='General'},
                        folder_groups=mapping,max_attempts=attempts,
                        relative_reports=self.relative_reports.get(),include_unencrypted=self.include_unencrypted.get())
    def _scan(self):
        try:
            _,_,files=scan(self._settings())
            messagebox.showinfo('Scan complete',f'{len(files)} PDF files found. No files modified.')
        except Exception as e:messagebox.showerror('Scan error',str(e))
    def _start(self,analyze):
        if self.worker and self.worker.is_alive():return
        try:
            s=self._settings(analyze);_,_,files=scan(s)
        except Exception as e:messagebox.showerror('Configuration error',str(e));return
        if not files:messagebox.showinfo('No files','No matching PDF files found.');return
        if not (analyze or s.dry_run) and not messagebox.askyesno('Confirm batch',f'Process {len(files)} PDFs?\nOriginals remain unchanged.\nExisting outputs will not be overwritten.'):
            return
        for item,_ in getattr(self,'row_items',[]):self.table.delete(item)
        self.counts={};self.row_items=[];self.filter_status.set('All statuses')
        self.bar['maximum']=len(files);self.bar['value']=0;self.stop_flag=threading.Event()
        self.start_btn.config(state='disabled');self.analyze_btn.config(state='disabled')
        self.scan_btn.config(state='disabled');self.stop_btn.config(state='normal')
        self.status.set('Processing...')
        self.worker=threading.Thread(target=self._work,args=(s,),daemon=True);self.worker.start()
    def _work(self,settings):
        try:process(settings,lambda kind,p:self.events.put((kind,p)),self.stop_flag)
        except Exception as e:self.events.put(('error',str(e)))
    def _stop(self):
        self.stop_flag.set();self.status.set('Finishing current qpdf attempt before stopping...')
    def _poll(self):
        try:
            while True:
                kind,p=self.events.get_nowait()
                if kind=='result':
                    self.bar['value']=p['index'];self.counts[p['status']]=self.counts.get(p['status'],0)+1
                    name=os.path.relpath(p['source'],self.source.get())
                    values=(p['status'],p.get('security',''),p.get('group',''),name,p['attempts'],p['elapsed_seconds'])
                    item=self.table.insert('','end',values=values);self.row_items.append((item,values))
                    if self.filter_status.get() not in ('All statuses',p['status']):self.table.detach(item)
                    self.status.set(f"{p['index']}/{p['total']} · "+' · '.join(f'{k}: {v}' for k,v in sorted(self.counts.items())))
                elif kind=='done':
                    self._done();self.last_report=p['report'] or ''
                    self.status.set(self.status.get()+(' · Cancelled' if p['cancelled'] else ' · Complete')+(f" · CSV: {p['report']}" if p['report'] else ''))
                elif kind=='error':
                    self._done();messagebox.showerror('Processing error',p)
        except queue.Empty:pass
        self.after(120,self._poll)
    def _done(self):
        self.start_btn.config(state='normal');self.analyze_btn.config(state='normal')
        self.scan_btn.config(state='normal');self.stop_btn.config(state='disabled')
    def _close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno('Processing','Stop and wait for current attempt?'):return
            self.stop_flag.set();self.after(200,self._wait_close)
        else:self._shutdown()
    def _wait_close(self):
        if self.worker and self.worker.is_alive():self.after(200,self._wait_close)
        else:self._shutdown()
    def _shutdown(self):
        for passwords in self.password_groups.values():passwords.clear()
        self.pw_entry.delete(0,'end');self.destroy()

if __name__=='__main__':App().mainloop()
