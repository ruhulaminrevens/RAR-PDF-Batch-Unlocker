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
from core import Settings, process, scan, FAILED
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
        self.title(f'{APP_NAME} · {VERSION}')
        width=min(1320,self.winfo_screenwidth()-60)
        height=min(960,self.winfo_screenheight()-80)
        self.geometry(f'{width}x{height}+20+20');self.minsize(1000,650)
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
        self.protocol('WM_DELETE_WINDOW',self._close)

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
            if (selected=='All statuses' or values[0]==selected) and (not query or query in ' '.join(map(str,values)).casefold()):
                self.table.move(item,'','end')

    def _select_result(self,table):
        selected=table.selection()
        if selected:
            record=self.result_records.get(selected[0],{})
            self.result_detail.set(record.get('details',''))

    def _open_path(self,path):
        if not path or not Path(path).exists():
            messagebox.showinfo('Not available','Complete a run first, or check that the file or folder still exists.');return
        try:
            if sys.platform=='win32':os.startfile(str(Path(path).resolve()))
            else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(Path(path).resolve())])
        except OSError as exc:messagebox.showerror('Could not open',str(exc))

    def _open_report(self):self._open_path(self.last_report)
    def _open_output(self):self._open_path(self.last_output or self.destination.get())

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
        if pw not in arr:arr.append(pw)
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
        if not self.source.get() or not self.destination.get():raise ValueError('Choose source and output folders.')
        return Settings(Path(self.source.get()),Path(self.destination.get()),self.qpdf.get() or 'qpdf',
                        list(self.password_groups['General']),limit,self.dry_run.get(),
                        analyze_only=analyze,failed_report=self.retry_report.get().strip(),
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
            source,_,files=scan(settings)
            self.events.put(('prepared',{'settings':settings,'mode':mode,'source':source,'count':len(files)}))
        except Exception as exc:self.events.put(('error',str(exc)))

    def _prepared(self,payload):
        if self.closing:return
        if self.stop_flag.is_set():
            self._done();self.status.set('Scan cancelled. No files changed.');return
        settings=payload['settings'];count=payload['count']
        self.total=count;self.metric_vars['total'].set(str(count))
        if payload['mode']=='scan':
            self._done();self.status.set(f'{count} matching PDFs found. No files modified.');return
        if not count:
            self._done();self.status.set('No matching PDF files found. Check your folders, limit or retry report.');return
        if not (settings.analyze_only or settings.dry_run) and not messagebox.askyesno('Confirm batch',f'Process {count} PDFs?\nOriginals remain unchanged.\nExisting outputs will not be overwritten.',parent=self):
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
        name=os.path.relpath(p['source'],self.active_source)
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
        self.metric_vars['skipped'].set(str(sum(v for k,v in self.counts.items() if k.startswith('Skipped'))))

    @staticmethod
    def _duration(seconds):
        value=max(0,int(seconds));return f'{value//60:02d}:{value%60:02d}'

    def _update_timing(self):
        if self.started_at is None:return
        elapsed=time.monotonic()-self.started_at
        eta=(elapsed/self.completed*(self.total-self.completed)) if self.completed else None
        remaining=self._duration(eta) if eta is not None else '—'
        self.timing.set(f"Elapsed {self._duration(elapsed)}   •   Estimated remaining {remaining}" if self.busy else f'Elapsed {self._duration(elapsed)}')

    def _poll(self):
        try:
            # Bound UI work per tick so Stop and navigation remain responsive.
            for _ in range(100):
                kind,p=self.events.get_nowait()
                if self.closing:continue
                if kind=='prepared':self._prepared(p)
                elif kind=='scan':self.total=p['count'];self.metric_vars['total'].set(str(self.total))
                elif kind=='result':self._result(p)
                elif kind=='done':
                    self._done();self.last_report=p['report'] or ''
                    self.report_text.set(f"CSV: {self.last_report}" if self.last_report else 'No report created (dry run).')
                    self.status.set(f"{'Stopped safely' if p['cancelled'] else 'Complete'} · {self.completed} of {self.total} PDFs")
                elif kind=='error':
                    self._done();self.status.set('Processing could not finish. Review the error and your settings.')
                    messagebox.showerror('Processing error',p)
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
        if self.poll_id:self.after_cancel(self.poll_id)
        self.pw_entry.delete(0,'end');self.destroy()

if __name__=='__main__':App().mainloop()
