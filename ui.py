"""Native Tk/ttk workspace. Presentation only; qpdf operations stay in core.py."""
import tkinter as tk
from tkinter import ttk
from branding import VERSION, apply_window_icon, asset_path

BG = '#090f1d'
SURFACE = '#101c30'
INSET = '#0b1425'
BORDER = '#26364f'
TEXT = '#ecf3ff'
MUTED = '#a1b1ca'
CYAN = '#5cdeed'
BLUE = '#356cf0'
VIOLET = '#aa9bff'
GREEN = '#5fe0b0'
AMBER = '#ffcb7c'
RED = '#ff929d'

STATUS_LABELS = {
    'Unlocked':'Unlocked', 'PasswordNotMatched':'No password match',
    'PasswordRequired':'Password required', 'PermissionRestricted':'Permission restricted',
    'Unencrypted':'Unencrypted', 'SkippedUnencrypted':'Already unencrypted',
    'CopiedUnencrypted':'Copied unencrypted', 'SkippedExisting':'Output exists',
    'InspectionFailed':'Inspection failed', 'VerificationFailed':'Verification failed',
    'InvalidPDF':'Invalid PDF', 'Timeout':'Timed out', 'Error':'Error',
    'Cancelled':'Cancelled', 'DryRun':'Dry run', 'DecryptFailed':'Rebuild failed',
    'FileLocked':'File locked', 'AccessDenied':'Access denied', 'DiskFull':'Disk full',
    'PathTooLong':'Path too long', 'SourceMissing':'Source missing', 'OutputConflict':'Name conflict',
}
LABEL_TO_STATUS = {v: k for k, v in STATUS_LABELS.items()}


class ScrollPage(ttk.Frame):
    """Independent vertical scrolling keeps controls reachable at high DPI."""
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas=tk.Canvas(self,bg=BG,highlightthickness=0,bd=0)
        bar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.body=ttk.Frame(self.canvas,padding=(22,18,22,22))
        self.window=self.canvas.create_window((0,0),window=self.body,anchor='nw')
        self.body.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.window,width=e.width))


class ModernUI:
    def px(self, value):
        """Scale a 96-DPI pixel size to the current Windows display scaling."""
        return int(round(value * self.ui_scale))

    def _build(self):
        self.ui_scale = max(1.0, float(self.tk.call('tk', 'scaling')) * 72 / 96)
        self.configure(bg=BG)
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background=BG,foreground=TEXT)
        style.configure('TFrame',background=BG)
        style.configure('TLabel',background=BG,foreground=TEXT)
        style.configure('Muted.TLabel',foreground=MUTED)
        style.configure('Title.TLabel',font=('Segoe UI',24,'bold'))
        style.configure('Section.TLabel',font=('Segoe UI',13,'bold'),background=SURFACE)
        style.configure('Card.TFrame',background=SURFACE)
        style.configure('Card.TLabel',background=SURFACE)
        style.configure('Note.TLabel',background=SURFACE,foreground=MUTED)
        style.configure('TButton',padding=(12,9),background='#1a2c46',foreground=TEXT,borderwidth=1,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,focuscolor=CYAN)
        style.map('TButton',background=[('disabled','#152238'),('active','#294362')],foreground=[('disabled','#73849c')],bordercolor=[('focus',CYAN)])
        style.configure('Primary.TButton',background=BLUE,foreground='#ffffff',font=('Segoe UI',10,'bold'),bordercolor=BLUE,lightcolor=BLUE,darkcolor=BLUE)
        style.map('Primary.TButton',background=[('disabled','#233a62'),('active','#497ff7')],foreground=[('disabled','#8b9db8')])
        style.configure('Danger.TButton',foreground=RED)
        style.configure('Nav.TButton',anchor='w',padding=(16,14),background=INSET,borderwidth=0)
        style.map('Nav.TButton',background=[('active','#152540')])
        style.configure('Active.Nav.TButton',background='#193663',foreground='#8fe9f5',font=('Segoe UI',10,'bold'))
        style.map('Active.Nav.TButton',background=[('active','#21447a')])
        style.configure('TEntry',fieldbackground=INSET,foreground=TEXT,insertcolor=TEXT,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,padding=(9,8))
        style.map('TEntry',fieldbackground=[('disabled','#131f32')],foreground=[('disabled','#8393ab')],bordercolor=[('focus',CYAN)])
        style.configure('TCombobox',fieldbackground=INSET,background='#1a2c46',foreground=TEXT,arrowcolor=CYAN,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,padding=7)
        style.map('TCombobox',fieldbackground=[('readonly',INSET),('disabled','#131f32')],foreground=[('readonly',TEXT),('disabled','#8393ab')],selectbackground=[('readonly',INSET)],selectforeground=[('readonly',TEXT)])
        style.configure('TCheckbutton',background=SURFACE,foreground=TEXT,indicatorbackground=INSET,indicatorforeground=CYAN,padding=(0,6))
        style.map('TCheckbutton',background=[('active',SURFACE)],foreground=[('disabled','#8393ab')],indicatorbackground=[('selected',BLUE)])
        style.configure('Treeview',background=INSET,fieldbackground=INSET,foreground=TEXT,rowheight=self.px(30),borderwidth=0,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER,font=('Segoe UI',10))
        style.map('Treeview',background=[('selected','#224b75')],foreground=[('selected','#ffffff')])
        style.configure('Treeview.Heading',background='#1b2b43',foreground=MUTED,font=('Segoe UI',9,'bold'),padding=(9,10),relief='flat')
        style.map('Treeview.Heading',background=[('active','#263d5b')])
        style.configure('Horizontal.TProgressbar',background=CYAN,troughcolor='#1c2b42',bordercolor='#1c2b42',lightcolor=CYAN,darkcolor=CYAN,borderwidth=0,thickness=7)
        style.configure('TScrollbar',background='#2c4364',troughcolor=BG,arrowcolor=MUTED,borderwidth=0,bordercolor=BG,lightcolor='#2c4364',darkcolor='#2c4364',gripcount=0)
        self.option_add('*TCombobox*Listbox.background',INSET)
        self.option_add('*TCombobox*Listbox.foreground',TEXT)
        self.option_add('*TCombobox*Listbox.selectBackground','#284e7c')
        self.option_add('*TCombobox*Listbox.selectForeground',TEXT)
        apply_window_icon(self)
        self.mutables=[];self.pages={};self.nav={}
        sidebar=tk.Frame(self,bg=INSET,width=self.px(210));sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        self.logo=tk.PhotoImage(file=str(asset_path('app-48.png')))
        tk.Label(sidebar,image=self.logo,bg=INSET).pack(anchor='w',padx=20,pady=(25,8))
        tk.Label(sidebar,text='RAR PDF',font=('Segoe UI',20,'bold'),fg=TEXT,bg=INSET).pack(anchor='w',padx=22)
        tk.Label(sidebar,text='BATCH UNLOCKER',font=('Segoe UI',9,'bold'),fg=MUTED,bg=INSET).pack(anchor='w',padx=22,pady=(2,28))
        for key,label in [('workspace','01    Batch workspace'),('passwords','02    Passwords'),('results','03    Results & reports'),('tools','04    PDF tools'),('settings','05    Run settings'),('help','06    About & help')]:
            btn=ttk.Button(sidebar,text=label,style='Nav.TButton',command=lambda k=key:self._navigate(k))
            btn.pack(fill='x',padx=10,pady=3);self.nav[key]=btn
        tk.Frame(sidebar,bg=CYAN,height=2).pack(side='bottom',fill='x',padx=22,pady=20)
        tk.Label(sidebar,text=f'RAR TOOLS  /  {VERSION}',font=('Segoe UI',9),fg=MUTED,bg=INSET).pack(side='bottom',anchor='w',padx=22)
        tk.Label(sidebar,text='LOCAL. PRIVATE. YOURS.',font=('Segoe UI',9,'bold'),fg=CYAN,bg=INSET).pack(side='bottom',anchor='w',padx=22,pady=10)
        self.session_summary=tk.StringVar(value='0 session passwords')
        tk.Label(sidebar,textvariable=self.session_summary,fg=MUTED,bg=INSET,font=('Segoe UI',9)).pack(side='bottom',anchor='w',padx=22,pady=3)
        host=ttk.Frame(self);host.pack(side='left',fill='both',expand=True)
        for key in self.nav:
            page=ScrollPage(host);self.pages[key]=page
        self._workspace(self.pages['workspace'].body)
        self._password_page(self.pages['passwords'].body)
        self._results_page(self.pages['results'].body)
        self._tools_page(self.pages['tools'].body)
        self._settings_page(self.pages['settings'].body)
        self._help_page(self.pages['help'].body)
        self.bind_all('<MouseWheel>',self._wheel,add='+')
        self.bind_all('<Button-4>',self._wheel,add='+');self.bind_all('<Button-5>',self._wheel,add='+')
        self._navigate('workspace')

    def _remember(self,widget,normal='normal'):
        self.mutables.append((widget,normal));return widget

    def _button(self,parent,text,command,primary=False,mutable=True,**kwargs):
        w=ttk.Button(parent,text=text,command=command,style='Primary.TButton' if primary else 'TButton',**kwargs)
        if mutable:self._remember(w)
        return w

    def _heading(self,parent,eyebrow,title,subtitle):
        ttk.Label(parent,text=eyebrow,foreground=CYAN,font=('Segoe UI',9,'bold')).pack(anchor='w')
        ttk.Label(parent,text=title,style='Title.TLabel').pack(anchor='w',pady=(6,4))
        ttk.Label(parent,text=subtitle,style='Muted.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(0,18))

    def _card(self,parent,title,subtitle='',**pack):
        shell=tk.Frame(parent,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1)
        shell.pack(fill='x',pady=(0,12),**pack)
        body=ttk.Frame(shell,style='Card.TFrame',padding=16);body.pack(fill='both',expand=True)
        ttk.Label(body,text=title,style='Section.TLabel').pack(anchor='w')
        if subtitle:ttk.Label(body,text=subtitle,style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(4,12))
        return body

    def _workspace(self,parent):
        self._heading(parent,'SECURE OFFLINE WORKSPACE','Your PDFs. Unlocked.','Analyze protection, use your known passwords and keep every original intact.')
        metrics=ttk.Frame(parent);metrics.pack(fill='x',pady=(0,16))
        self.metric_vars={}
        for i,(key,label,color) in enumerate([('total','PDFs IN LAST SCAN',CYAN),('unlocked','UNLOCKED',GREEN),('attention','NEED ATTENTION',AMBER),('skipped','SKIPPED',VIOLET)]):
            metrics.columnconfigure(i,weight=1,uniform='metric')
            card=tk.Frame(metrics,bg=SURFACE,highlightthickness=1,highlightbackground=BORDER)
            card.grid(row=0,column=i,sticky='nsew',padx=(0,8 if i<3 else 0))
            tk.Frame(card,bg=color,height=2).pack(fill='x')
            var=tk.StringVar(value='—');self.metric_vars[key]=var
            tk.Label(card,textvariable=var,font=('Segoe UI',26,'bold'),bg=SURFACE,fg=color).pack(anchor='w',padx=14,pady=(9,0))
            tk.Label(card,text=label,font=('Segoe UI',8,'bold'),bg=SURFACE,fg=MUTED).pack(anchor='w',padx=14,pady=(2,12))
        drag=' Drag a folder or PDFs onto these boxes.' if getattr(self,'dnd_enabled',False) else ''
        paths=self._card(parent,'01   Inputs & output','Choose a source folder, add individual PDFs, or both. Output must be a separate folder; subfolders are preserved.'+drag)
        self.path_entries={}
        for label,var,is_folder,drop in [('Source folder',self.source,True,self._drop_source),('Output folder',self.destination,True,self._drop_output)]:
            row=ttk.Frame(paths,style='Card.TFrame');row.pack(fill='x',pady=4)
            ttk.Label(row,text=label,width=14,style='Card.TLabel').pack(side='left')
            ent=self._remember(ttk.Entry(row,textvariable=var));ent.pack(side='left',fill='x',expand=True,padx=(0,8));self.path_entries[label]=ent
            self._drop_target(ent,drop)
            self._button(row,'Browse',lambda v=var,f=is_folder:self._browse(v,f)).pack(side='right')
        row=ttk.Frame(paths,style='Card.TFrame');row.pack(fill='x',pady=4)
        ttk.Label(row,text='Single PDFs',width=14,style='Card.TLabel').pack(side='left')
        self._button(row,'Clear',self._clear_files).pack(side='right')
        self._button(row,'Add PDFs…',self._add_files).pack(side='right',padx=(0,8))
        files_lbl=ttk.Label(row,textvariable=self.files_summary,style='Note.TLabel',width=1);files_lbl.pack(side='left',fill='x',expand=True,padx=(0,8))
        self._drop_target(files_lbl,lambda paths:self._add_extra_files(paths))
        row=ttk.Frame(paths,style='Card.TFrame');row.pack(fill='x',pady=(9,0))
        self.scan_btn=self._button(row,'Scan filenames',self._scan);self.scan_btn.pack(side='left')
        self.analyze_btn=self._button(row,'Analyze security',lambda:self._start(True));self.analyze_btn.pack(side='left',padx=8)
        self._button(row,'Manage passwords  →',lambda:self._navigate('passwords'),mutable=False).pack(side='right')
        run=self._card(parent,'02   Run your batch')
        ttk.Label(run,textvariable=self.mode_summary,style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(8,10))
        row=ttk.Frame(run,style='Card.TFrame');row.pack(fill='x')
        self.start_btn=self._button(row,'Unlock batch   →',lambda:self._start(False),primary=True);self.start_btn.pack(side='left')
        self.stop_btn=ttk.Button(row,text='Stop safely',command=self._stop,state='disabled',style='Danger.TButton');self.stop_btn.pack(side='left',padx=8)
        self._button(row,'Run settings',lambda:self._navigate('settings'),mutable=False).pack(side='right')
        self._progress(run)
        preview=self._card(parent,'03   Latest results')
        self.preview_table=self._make_table(preview,compact=True,height=4)
        footer=ttk.Frame(preview,style='Card.TFrame');footer.pack(fill='x',pady=(10,0))
        ttk.Label(footer,text='Originals preserved  •  Existing outputs always skipped',style='Note.TLabel').pack(side='left')
        self._button(footer,'View all results  →',lambda:self._navigate('results'),mutable=False).pack(side='right')

    def _progress(self,parent):
        ttk.Progressbar(parent,mode='determinate',maximum=100,variable=self.progress).pack(fill='x',pady=(17,10))
        row=ttk.Frame(parent,style='Card.TFrame');row.pack(fill='x')
        ttk.Label(row,textvariable=self.status,style='Card.TLabel',wraplength=self.px(600)).pack(side='left',anchor='w')
        ttk.Label(row,textvariable=self.progress_text,style='Note.TLabel').pack(side='right')
        ttk.Label(parent,textvariable=self.timing,style='Note.TLabel').pack(anchor='w',pady=(7,0))

    def _password_page(self,parent):
        self._heading(parent,'KNOWN PASSWORDS','Private by default.','Passwords stay in this session unless you explicitly save a named Windows vault entry.')
        card=self._card(parent,'Session password groups','A matching folder group is tried first, followed by General passwords. Values never appear in reports.')
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x')
        self.groupbox=self._remember(ttk.Combobox(row,textvariable=self.group,values=['General'],state='readonly',width=24),'readonly');self.groupbox.pack(side='left')
        self.groupbox.bind('<<ComboboxSelected>>',lambda e:self._update_count())
        self._button(row,'New group',self._new_group).pack(side='left',padx=8)
        self._button(row,'Clear group',self._clear).pack(side='right')
        self._button(row,'Delete group',self._delete_group).pack(side='right',padx=8)
        ttk.Label(card,textvariable=self.pw_count,style='Note.TLabel').pack(anchor='w',pady=(12,6))
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x')
        self.pw_entry=self._remember(ttk.Entry(row,show='●'));self.pw_entry.pack(side='left',fill='x',expand=True)
        self.pw_entry.bind('<Return>',lambda e:self._add_password())
        self._remember(ttk.Checkbutton(row,text='Show',variable=self.show_password,command=self._toggle_password)).pack(side='left',padx=10)
        self._button(row,'Add to group',self._add_password,primary=True).pack(side='right')
        ttk.Label(card,text='Tip: Enter adds a password. The field clears after adding; duplicates are ignored.',style='Note.TLabel').pack(anchor='w',pady=(12,0))
        mapping=self._card(parent,'Folder → group mapping','One relative folder=Group Name per line. The most specific folder wins.')
        frame=ttk.Frame(mapping,style='Card.TFrame');frame.pack(fill='x')
        self.mapping=self._remember(tk.Text(frame,height=5,wrap='none',bg=INSET,fg=TEXT,insertbackground=CYAN,selectbackground='#284e7c',relief='flat',highlightthickness=1,highlightbackground=BORDER,font=('Consolas',11),padx=10,pady=10))
        self.mapping.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.mapping.yview);scroll.pack(side='right',fill='y');self.mapping.configure(yscrollcommand=scroll.set)
        ttk.Label(mapping,text='Example: Statements=Bank    or    Office/Invoices=Company',style='Note.TLabel').pack(anchor='w',pady=(8,0))
        vault=self._card(parent,'Windows Credential Locker  ·  optional','Save the password currently in the entry field, or load a named credential into the selected group.')
        row=ttk.Frame(vault,style='Card.TFrame');row.pack(fill='x')
        for label,fn in [('Save entered password',self._save_vault),('Load saved password',self._load_vault),('Delete saved password',self._delete_vault)]:
            self._button(row,label,fn).pack(side='left',padx=(0,8))
        ttk.Label(vault,text='Uses your Windows account’s credential store. No password file is created by this app.',style='Note.TLabel',wraplength=self.px(740)).pack(anchor='w',pady=(12,0))

    def _make_table(self,parent,compact=False,height=12):
        container=ttk.Frame(parent,style='Card.TFrame');container.pack(fill='both',expand=True,pady=(10,0))
        cols=('status','filename') if compact else ('status','filename','security','group','attempts','seconds')
        table=ttk.Treeview(container,columns=cols,show='headings',height=height)
        widths={k:self.px(v) for k,v in {'status':165,'filename':300,'security':160,'group':110,'attempts':85,'seconds':80}.items()}
        for key in cols:
            table.heading(key,text={'filename':'PDF FILE  /  RELATIVE PATH','seconds':'TIME (s)'}.get(key,key.upper()),command=lambda k=key,t=table:self._sort_table(t,k))
            table.column(key,width=widths[key],minwidth=self.px(220) if key=='filename' else widths[key],stretch=(key=='filename'),anchor='center' if key in ('attempts','seconds') else 'w')
        table.grid(row=0,column=0,sticky='nsew');container.columnconfigure(0,weight=1);container.rowconfigure(0,weight=1)
        vbar=ttk.Scrollbar(container,orient='vertical',command=table.yview);vbar.grid(row=0,column=1,sticky='ns')
        hbar=ttk.Scrollbar(container,orient='horizontal',command=table.xview);hbar.grid(row=1,column=0,sticky='ew')
        table.configure(yscrollcommand=vbar.set,xscrollcommand=hbar.set)
        for tag,color in [('good',GREEN),('warn',AMBER),('error',RED),('skip',VIOLET),('neutral',TEXT)]:table.tag_configure(tag,foreground=color)
        table.tag_configure('odd',background='#111e32')
        table.bind('<<TreeviewSelect>>',lambda e,t=table:self._select_result(t))
        return table

    def _results_page(self,parent):
        self._heading(parent,'BATCH EVIDENCE','Results & reports','Review the latest run, filter by status and retry failed records from a CSV report.')
        card=self._card(parent,'Live results','The table contains this session’s latest run. CSV reports remain in your output folder.')
        self._progress(card)
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x',pady=(14,0))
        ttk.Label(row,text='Search',style='Card.TLabel').pack(side='left',padx=(0,6))
        ttk.Entry(row,textvariable=self.search).pack(side='left',fill='x',expand=True,padx=(0,10))
        self.filterbox=ttk.Combobox(row,textvariable=self.filter_status,values=['All statuses','Needs attention',*STATUS_LABELS],state='readonly',width=24);self.filterbox.pack(side='right')
        self.filterbox.bind('<<ComboboxSelected>>',lambda e:self._filter_rows())
        self.table=self._make_table(card)
        ttk.Label(card,textvariable=self.result_detail,style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(10,0))
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x',pady=(12,0))
        self.report_btn=self._button(row,'Open CSV report',self._open_report,mutable=False);self.report_btn.pack(side='left')
        self._button(row,'Open HTML summary',self._open_html,mutable=False).pack(side='left',padx=8)
        self._button(row,'Open output folder',self._open_output,mutable=False).pack(side='left')
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x',pady=(8,0))
        self.retry_btn=self._button(row,'Retry failures from last report',self._use_last_report);self.retry_btn.pack(side='left')
        ttk.Label(card,textvariable=self.report_text,style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(12,0))
        self.search.trace_add('write',lambda *a:self._filter_rows())

    def _tools_page(self,parent):
        drag=' You can drag files straight onto the lists and boxes below.' if getattr(self,'dnd_enabled',False) else ''
        self._heading(parent,'OFFLINE PDF TOOLKIT','PDF tools','Merge, split, reorganize, convert between images and PDF, and export a draft to Word or Excel. Everything runs on this PC; nothing is uploaded.'+drag)
        self.tool_status=tk.StringVar(value='Choose a tool below. Protected PDFs must be unlocked first (Batch workspace).')
        bar=self._card(parent,'Status')
        ttk.Label(bar,textvariable=self.tool_status,style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(4,0))

        # 1. Merge
        m=self._card(parent,'Merge PDFs','Combine several PDFs into one, in the order shown. Use Up/Down to reorder.')
        self.merge_list=self._file_listbox(m)
        self._drop_target(self.merge_list,lambda paths:self._add_paths_to_list(self.merge_list,'pdf',paths))
        row=ttk.Frame(m,style='Card.TFrame');row.pack(fill='x',pady=(8,0))
        self._button(row,'Add PDFs…',lambda:self._tool_add(self.merge_list,'pdf')).pack(side='left')
        self._button(row,'Remove',lambda:self._tool_remove(self.merge_list)).pack(side='left',padx=6)
        self._button(row,'Up',lambda:self._tool_move(self.merge_list,-1)).pack(side='left')
        self._button(row,'Down',lambda:self._tool_move(self.merge_list,1)).pack(side='left',padx=6)
        self._button(row,'Clear',lambda:self._tool_clear(self.merge_list)).pack(side='left')
        self._button(m,'Merge into one PDF…',self._tool_merge,primary=True).pack(anchor='w',pady=(10,0))

        # 2. Split / organize
        s=self._card(parent,'Split & organize','Split one PDF into pieces, or keep/reorder/rotate pages. Pages like 1,3-5,8.')
        self.split_input=tk.StringVar()
        self._tool_input_row(s,self.split_input,'Source PDF')
        row=ttk.Frame(s,style='Card.TFrame');row.pack(fill='x',pady=(6,0))
        ttk.Label(row,text='Pages',width=self.px(14),style='Card.TLabel').pack(side='left')
        self._remember(ttk.Entry(row,textvariable=self._mk('split_pages',''))).pack(side='left',fill='x',expand=True,padx=(0,8))
        row=ttk.Frame(s,style='Card.TFrame');row.pack(fill='x',pady=(6,0))
        ttk.Label(row,text='Rotate',width=self.px(14),style='Card.TLabel').pack(side='left')
        self.split_rotate=tk.StringVar(value='0')
        self._remember(ttk.Combobox(row,textvariable=self.split_rotate,values=['0','90','180','270'],state='readonly',width=8),'readonly').pack(side='left')
        ttk.Label(row,text='degrees, applied to the kept pages',style='Note.TLabel').pack(side='left',padx=8)
        row=ttk.Frame(s,style='Card.TFrame');row.pack(fill='x',pady=(10,0))
        self._button(row,'Split every page…',lambda:self._tool_split('each'),primary=True).pack(side='left')
        self._button(row,'Export selected pages…',lambda:self._tool_split('keep')).pack(side='left',padx=8)

        # 3. Image -> PDF
        i=self._card(parent,'Images → PDF','Combine images (jpg, png, bmp, tiff, webp) into one PDF, in the order shown.')
        self.img_list=self._file_listbox(i)
        self._drop_target(self.img_list,lambda paths:self._add_paths_to_list(self.img_list,'img',paths))
        row=ttk.Frame(i,style='Card.TFrame');row.pack(fill='x',pady=(8,0))
        self._button(row,'Add images…',lambda:self._tool_add(self.img_list,'img')).pack(side='left')
        self._button(row,'Remove',lambda:self._tool_remove(self.img_list)).pack(side='left',padx=6)
        self._button(row,'Up',lambda:self._tool_move(self.img_list,-1)).pack(side='left')
        self._button(row,'Down',lambda:self._tool_move(self.img_list,1)).pack(side='left',padx=6)
        self._button(row,'Clear',lambda:self._tool_clear(self.img_list)).pack(side='left')
        self._button(i,'Make PDF from images…',self._tool_img2pdf,primary=True).pack(anchor='w',pady=(10,0))

        # 4. PDF -> images
        pi=self._card(parent,'PDF → images','Save each page as an image. Larger DPI means sharper, bigger files.')
        self.rimg_input=tk.StringVar()
        self._tool_input_row(pi,self.rimg_input,'Source PDF')
        row=ttk.Frame(pi,style='Card.TFrame');row.pack(fill='x',pady=(6,0))
        ttk.Label(row,text='Format',width=self.px(14),style='Card.TLabel').pack(side='left')
        self.rimg_fmt=tk.StringVar(value='png')
        self._remember(ttk.Combobox(row,textvariable=self.rimg_fmt,values=['png','jpg','tiff','webp'],state='readonly',width=8),'readonly').pack(side='left')
        ttk.Label(row,text='DPI',style='Card.TLabel').pack(side='left',padx=(16,6))
        self.rimg_dpi=tk.StringVar(value='150')
        self._remember(ttk.Combobox(row,textvariable=self.rimg_dpi,values=['72','100','150','200','300'],state='readonly',width=6),'readonly').pack(side='left')
        self._button(pi,'Export pages as images…',self._tool_pdf2img,primary=True).pack(anchor='w',pady=(10,0))

        # 5/6. PDF -> Word / Excel
        c=self._card(parent,'PDF → Word / Excel  ·  draft','Text-based draft export. Works on PDFs with selectable text; scanned (image-only) PDFs need OCR, which is not included.')
        self.conv_input=tk.StringVar()
        self._tool_input_row(c,self.conv_input,'Source PDF')
        row=ttk.Frame(c,style='Card.TFrame');row.pack(fill='x',pady=(10,0))
        self._button(row,'Export to Word (.docx)…',lambda:self._tool_convert('docx'),primary=True).pack(side='left')
        self._button(row,'Export to Excel (.xlsx)…',lambda:self._tool_convert('xlsx')).pack(side='left',padx=8)
        ttk.Label(c,text='Tip: for an exact copy to print, use “PDF → images” instead — layout is preserved.',style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(10,0))

    def _file_listbox(self,parent,height=4):
        frame=ttk.Frame(parent,style='Card.TFrame');frame.pack(fill='x',pady=(8,0))
        box=tk.Listbox(frame,height=height,bg=INSET,fg=TEXT,selectbackground='#284e7c',selectforeground=TEXT,
                       relief='flat',highlightthickness=1,highlightbackground=BORDER,activestyle='none',font=('Segoe UI',10))
        box.pack(side='left',fill='both',expand=True)
        bar=ttk.Scrollbar(frame,orient='vertical',command=box.yview);bar.pack(side='right',fill='y');box.configure(yscrollcommand=bar.set)
        box._paths=[]
        self._remember(box)
        return box

    def _tool_input_row(self,parent,var,label):
        row=ttk.Frame(parent,style='Card.TFrame');row.pack(fill='x',pady=(8,0))
        ttk.Label(row,text=label,width=self.px(14),style='Card.TLabel').pack(side='left')
        ent=self._remember(ttk.Entry(row,textvariable=var));ent.pack(side='left',fill='x',expand=True,padx=(0,8))
        self._drop_target(ent,lambda paths,v=var:self._drop_single_pdf(v,paths))
        self._button(row,'Browse',lambda:self._tool_pick_file(var)).pack(side='right')

    def _mk(self,name,value):
        var=tk.StringVar(value=value);setattr(self,name,var);return var

    def _settings_page(self,parent):
        self._heading(parent,'CONTROLLED EXECUTION','Run settings','Set a small file limit for a first pass, then process the full batch when you are ready.')
        card=self._card(parent,'Processing limits','The empty-password check counts as an attempt. No brute-force or generated password list is used.')
        for label,var,hint in [('File limit',self.limit,'0 = all matching PDFs'),('Attempts per PDF',self.max_attempts,'1–1,000; default 30'),('Timeout per qpdf step (s)',self.timeout,'1–3,600; raise for very large PDFs'),('Parallel workers',self.workers,'1–16; files processed at the same time')]:
            row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x',pady=6)
            ttk.Label(row,text=label,width=22,style='Card.TLabel').pack(side='left')
            self._remember(ttk.Entry(row,textvariable=var,width=10)).pack(side='left',padx=(0,15))
            ttk.Label(row,text=hint,style='Note.TLabel').pack(side='left')
        card=self._card(parent,'Mode & privacy')
        for label,var in [('Dry run — list matching files; test no passwords and write no files',self.dry_run),('Copy already unencrypted PDFs into the output folder',self.include_unencrypted),('Use relative file paths in CSV reports (recommended)',self.relative_reports),('Also write a readable HTML summary',self.html_summary)]:
            self._remember(ttk.Checkbutton(card,text=label,variable=var)).pack(anchor='w',pady=2)
        ttk.Label(card,text='Analyze security inspects PDFs and writes a CSV, without creating unlocked PDFs.\nDry run takes priority when enabled. Existing output files are always preserved.',style='Note.TLabel',wraplength=self.px(760)).pack(anchor='w',pady=(8,0))
        card=self._card(parent,'Continue from a previous report','Retry processes only failed records. Resume skips verified, finished files and processes everything else, including files an interrupted run never reached. Use the same source selection as that run.')
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x',pady=(0,8))
        for text,value in [('Retry failed only','retry'),('Resume interrupted run','resume')]:
            self._remember(ttk.Radiobutton(row,text=text,value=value,variable=self.continue_mode)).pack(side='left',padx=(0,16))
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x')
        self._remember(ttk.Entry(row,textvariable=self.retry_report)).pack(side='left',fill='x',expand=True)
        self._button(row,'Choose CSV',self._select_report).pack(side='left',padx=8)
        self._button(row,'Clear',lambda:self.retry_report.set('')).pack(side='left')
        card=self._card(parent,'qpdf engine','The bundled engine is used automatically. Change this only to use another qpdf installation.')
        row=ttk.Frame(card,style='Card.TFrame');row.pack(fill='x')
        ent=self._remember(ttk.Entry(row,textvariable=self.qpdf));ent.pack(side='left',fill='x',expand=True,padx=(0,8));self.path_entries['qpdf engine']=ent
        self._button(row,'Browse',lambda:self._browse(self.qpdf,False)).pack(side='right')
        ttk.Label(card,textvariable=self.engine_text,style='Note.TLabel',wraplength=self.px(740)).pack(anchor='w',pady=(8,0))
        self._button(parent,'Back to batch workspace  →',lambda:self._navigate('workspace'),primary=True,mutable=False).pack(anchor='w')
        for var in (self.dry_run,self.include_unencrypted,self.relative_reports,self.limit,self.max_attempts,self.retry_report,self.continue_mode,self.workers):var.trace_add('write',lambda *a:self._update_mode())
        self._update_mode()

    def _help_page(self,parent):
        self._heading(parent,'RAR TOOLS',f'RAR PDF Batch Unlocker {VERSION}','A local Windows workspace for authorized PDF analysis and batch unlocking.')
        card=self._card(parent,'A simple workflow')
        text='1. Choose separate source and output folders; confirm the qpdf engine path.\n2. Scan filenames or analyze security to understand the batch.\n3. Add your known passwords, and map folders to groups if needed.\n4. Check run settings, then unlock. Review the results and CSV report.'
        ttk.Label(card,text=text,style='Card.TLabel',wraplength=self.px(760),justify='left').pack(anchor='w',pady=12)
        card=self._card(parent,'Built around your originals')
        ttk.Label(card,text='Original files are never intentionally overwritten. Existing outputs are skipped, and decrypted outputs are checked with qpdf before being accepted. Passwords go to qpdf through stdin, never command-line arguments.\n\nUnlocked documents remain sensitive. Keep the output folder access-controlled. Rewriting a digitally signed PDF can invalidate its signature.',style='Note.TLabel',wraplength=self.px(760),justify='left').pack(anchor='w',pady=10)
        self._button(card,'Read password recovery guidance',self._hints,mutable=False).pack(anchor='w')
        card=self._card(parent,'What this app can do')
        ttk.Label(card,text='Use only PDFs and passwords you are authorized to access. A strong unknown opening password cannot be bypassed by qpdf. There is no online upload, password guessing service or persistent history database in this app.\n\nThe Windows build is unsigned unless separately signed with an Authenticode certificate.',style='Note.TLabel',wraplength=self.px(760),justify='left').pack(anchor='w',pady=10)

    def _navigate(self,key):
        if hasattr(self,'pw_entry'):
            self.show_password.set(False);self.pw_entry.configure(show='●')
        for name,page in self.pages.items():
            page.pack_forget();self.nav[name].configure(style='Active.Nav.TButton' if name==key else 'Nav.TButton')
        self.pages[key].pack(fill='both',expand=True)
        self.active_page=key

    def _wheel(self,event):
        widget=event.widget
        if isinstance(widget,(tk.Text,ttk.Treeview,ttk.Combobox)):return
        page=self.pages.get(getattr(self,'active_page','workspace'))
        if page and page.body.winfo_reqheight()>page.canvas.winfo_height():
            delta=(-1 if event.num==4 else 1) if getattr(event,'num',None) in (4,5) else (-1 if event.delta>0 else 1)
            page.canvas.yview_scroll(delta*3,'units')

    def _toggle_password(self):
        self.pw_entry.configure(show='' if self.show_password.get() else '●')

    def _update_mode(self):
        mode='Dry run · no file changes' if self.dry_run.get() else 'Unlock using supplied passwords'
        limit=self.limit.get().strip()
        cont=('  •  Resume from report' if self.continue_mode.get()=='resume' else '  •  Failed-only retry') if self.retry_report.get() else ''
        self.mode_summary.set(f"{mode}  •  {'All files' if limit=='0' else 'Limit: '+limit}  •  {self.max_attempts.get()} attempts / PDF  •  {self.workers.get()} worker(s)"+cont)
        if hasattr(self,'start_btn'):self.start_btn.configure(text='Start dry run   →' if self.dry_run.get() else 'Unlock batch   →')
