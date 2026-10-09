import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowDownToLine, ArrowUpRight, Atom, Beaker, BookOpen,
  CheckCircle2, ChevronRight, CircleHelp, Clock3, Dna, FileCheck2,
  FilePlus2, FileText, FlaskConical, FolderClock, Gauge, GitBranch,
  LayoutDashboard, LoaderCircle, Microscope, Network, Search, ShieldAlert,
  Sparkles, UploadCloud, XCircle,
} from 'lucide-react';

const API = 'http://127.0.0.1:8000/api';
const ASPIRIN_SMILES = 'CC(=O)OC1=CC=CC=C1C(=O)O';

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(data?.detail || data?.message || `Request failed (${response.status})`);
  return data;
}

function IconLogo() {
  return <div className="brand-symbol"><Atom size={22} strokeWidth={1.8}/><span className="brand-dot"/></div>;
}
function StatusDot({ okay = false }) {
  return <span className={`status-dot ${okay ? 'is-ok' : ''}`} />;
}
function StatCard({ icon: Icon, label, value, hint, tone = 'teal' }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={18}/></div><div className="stat-main"><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-hint">{hint}</div></div></div>;
}
function SectionHeader({ eyebrow, title, subtitle, action }) {
  return <div className="section-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{action}</div>;
}
function EmptyState({ icon: Icon = FileText, title, copy }) {
  return <div className="empty-state"><span className="empty-icon"><Icon size={22}/></span><strong>{title}</strong><p>{copy}</p></div>;
}

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [health, setHealth] = useState(null);
  const [reports, setReports] = useState([]);
  const [history, setHistory] = useState([]);
  const [generatedReports, setGeneratedReports] = useState([]);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [currentDisease, setCurrentDisease] = useState(null);
  const [moleculeName, setMoleculeName] = useState('Aspirin');
  const [smiles, setSmiles] = useState(ASPIRIN_SMILES);
  const [selectedReport, setSelectedReport] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [analyzeBusy, setAnalyzeBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState('');
  const [apiUp, setApiUp] = useState(false);

  const refresh = async () => {
    try {
      const [h, r, hist, generated] = await Promise.all([api('/health'), api('/disease-reports'), api('/history'), api('/reports')]);
      setHealth(h); setReports(r); setHistory(hist); setGeneratedReports(generated); setApiUp(true);
    } catch (e) { setApiUp(false); setError(e.message); }
  };
  useEffect(() => { refresh(); }, []);

  const pageTitle = useMemo(() => ({
    dashboard: 'Overview', disease: 'Disease report analyzer', molecule: 'Molecular analysis',
    history: 'Analysis history', reports: 'Research reports', roadmap: 'Platform roadmap',
  }[page]), [page]);

  const flash = (kind, message) => { setNotice({ kind, message }); window.setTimeout(() => setNotice(null), 5000); };
  const go = (value) => { setPage(value); setError(''); setNotice(null); };

  async function uploadPDF() {
    if (!pdfFile) { setError('Choose a disease research PDF first.'); return; }
    setUploadBusy(true); setError('');
    try {
      const form = new FormData(); form.append('file', pdfFile);
      const result = await api('/disease-reports/upload', { method: 'POST', body: form });
      setCurrentDisease({ ...result, diseaseName: result.hints?.possible_disease_terms?.[0] || '', targetText: (result.hints?.possible_gene_or_protein_symbols || []).join(', ') }); setSelectedReport(result.id);
      await refresh(); flash('success', 'PDF text extracted. Please review the hints before confirming.');
    } catch (e) { setError(e.message); }
    finally { setUploadBusy(false); }
  }

  async function analyzeMolecule(e) {
    e?.preventDefault(); setAnalyzeBusy(true); setError('');
    try {
      const result = await api('/molecules/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ molecule_name: moleculeName, smiles, disease_report_id: selectedReport || null }),
      });
      setCurrentAnalysis(result); await refresh(); flash('success', 'Molecular descriptors calculated and saved.');
    } catch (e2) { setError(e2.message); }
    finally { setAnalyzeBusy(false); }
  }

  async function confirmDisease() {
    if (!currentDisease?.id) return;
    const targets = (currentDisease.targetText || '').split(',').map(x => x.trim()).filter(Boolean);
    try {
      const result = await api(`/disease-reports/${currentDisease.id}/confirm`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ disease_name: currentDisease.diseaseName || null, targets }),
      });
      flash('success', 'Your reviewed disease information was saved.');
      setSelectedReport(currentDisease.id); await refresh();
    } catch (e) { setError(e.message); }
  }

  async function makeReport(analysisId = currentAnalysis?.id) {
    if (!analysisId) return;
    setReportBusy(true); setError('');
    try {
      const result = await api('/reports/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ analysis_id: analysisId }) });
      await refresh();
      window.location.assign(`${API}${result.download_url.replace('/api', '')}`);
      flash('success', 'Analysis report generated.');
    } catch (e) { setError(e.message); }
    finally { setReportBusy(false); }
  }

  async function openHistory(item) {
    try {
      const result = await api(`/history/${item.id}`);
      setCurrentAnalysis({ id: result.id, molecule_name: result.molecule_name, smiles: result.smiles, disease_report_id: result.report_id, result: result.result, created_at: result.created_at });
      setMoleculeName(result.molecule_name || ''); setSmiles(result.smiles || ''); setSelectedReport(result.report_id || ''); setPage('molecule');
    } catch (e) { setError(e.message); }
  }

  const navGroups = [
    { title: 'WORKSPACE', items: [
      { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'disease', label: 'Disease report', icon: FilePlus2 },
      { id: 'molecule', label: 'Molecular analysis', icon: Atom },
      { id: 'history', label: 'Analysis history', icon: FolderClock },
    ] },
    { title: 'RESEARCH TOOLS', items: [
      { id: 'reports', label: 'Generated reports', icon: FileCheck2 },
      { id: 'roadmap', label: 'Integrations & roadmap', icon: GitBranch },
    ] },
  ];

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><IconLogo/><div><div className="brand-name">Chemora<span>-AI</span></div><div className="brand-sub">MOLECULAR RESEARCH</div></div></div>
      <div className="workspace-switch"><div className="workspace-mark">C</div><div className="workspace-meta"><strong>Research workspace</strong><span>Local prototype</span></div><ChevronRight size={15}/></div>
      {navGroups.map(group => <div className="nav-group" key={group.title}><div className="nav-caption">{group.title}</div>{group.items.map(item => <button className={`nav-link ${page === item.id ? 'active' : ''}`} key={item.id} onClick={() => go(item.id)}><item.icon size={17}/><span>{item.label}</span>{item.id === 'disease' && reports.length > 0 && <span className="nav-count">{reports.length}</span>}</button>)}</div>)}
      <div className="sidebar-bottom"><div className="science-note"><div className="science-note-icon"><ShieldAlert size={16}/></div><div><strong>Research prototype</strong><p>Computational screening is not proof of drug efficacy or safety.</p></div></div><div className="profile-row"><div className="profile-avatar">CA</div><div className="profile-text"><strong>Local analyst</strong><span>Demo workspace</span></div><span className="profile-menu">•••</span></div></div>
    </aside>

    <main className="main-panel">
      <header className="topbar"><div className="breadcrumb"><span>Workspace</span><ChevronRight size={14}/><strong>{pageTitle}</strong></div><div className="topbar-right"><div className="connection"><StatusDot okay={apiUp}/><span>{apiUp ? 'Backend connected' : 'Backend offline'}</span></div><div className="topbar-divider"/><div className="avatar-small">CA</div></div></header>
      <div className="page-content">
        {error && <div className="alert error"><XCircle size={17}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss"><XCircle size={16}/></button></div>}
        {notice && <div className={`alert ${notice.kind}`}><CheckCircle2 size={17}/><span>{notice.message}</span><button onClick={() => setNotice(null)} aria-label="Dismiss"><XCircle size={16}/></button></div>}

        {page === 'dashboard' && <>
          <SectionHeader eyebrow="RESEARCH OVERVIEW" title="Welcome to Chemora-AI" subtitle="A practical workspace for disease-literature intake and preliminary molecular screening." action={<button className="button primary" onClick={() => go('disease')}><UploadCloud size={16}/> Upload disease PDF</button>}/>
          <div className="hero-banner"><div className="hero-copy"><div className="hero-kicker"><Sparkles size={14}/> FROM DISEASE INSIGHTS TO CANDIDATE MOLECULES</div><h2>Turn research literature<br/>into a structured workflow.</h2><p>Upload a disease report, review extracted clues, analyze a molecule, and export a transparent computational report.</p><div className="hero-actions"><button className="button light" onClick={() => go('disease')}>Start with a PDF <ArrowUpRight size={15}/></button><button className="hero-text-button" onClick={() => go('molecule')}>Analyze a molecule</button></div></div><div className="hero-graphic"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="orbit-center"><Atom size={54}/></div><span className="orbit-label label-top">SMILES</span><span className="orbit-label label-right">RDKit</span><span className="orbit-label label-bottom">PDF → DATA</span></div></div>
          <div className="stat-grid"><StatCard icon={FileText} label="Disease PDFs" value={reports.length} hint="Documents uploaded"/><StatCard icon={Atom} label="Molecules analyzed" value={history.length} hint="Saved analyses" tone="blue"/><StatCard icon={FileCheck2} label="Reports generated" value={generatedReports.length} hint="Downloadable analysis PDFs" tone="purple"/><StatCard icon={Activity} label="API status" value={apiUp ? 'Online' : 'Offline'} hint={health?.rdkit ? `RDKit ${health.rdkit}` : 'Start the backend'} tone="green"/></div>
          <div className="content-grid"><div className="panel-card"><div className="panel-title-row"><div><h3>Research workflow</h3><p>Recommended order for a new analysis</p></div><span className="pill neutral">4 stages</span></div><div className="workflow-list"><div className="workflow-item"><div className="step-icon"><UploadCloud size={17}/></div><div className="workflow-text"><strong>Upload disease research</strong><span>Extract text and page-level context from a PDF.</span></div><button className="icon-button" onClick={() => go('disease')}><ChevronRight size={16}/></button></div><div className="workflow-item"><div className="step-icon"><Search size={17}/></div><div className="workflow-text"><strong>Review disease clues</strong><span>Inspect keyword hints and confirm target information.</span></div><button className="icon-button" onClick={() => go('disease')}><ChevronRight size={16}/></button></div><div className="workflow-item"><div className="step-icon"><FlaskConical size={17}/></div><div className="workflow-text"><strong>Analyze a molecule</strong><span>Calculate molecular descriptors using RDKit.</span></div><button className="icon-button" onClick={() => go('molecule')}><ChevronRight size={16}/></button></div><div className="workflow-item"><div className="step-icon"><FileCheck2 size={17}/></div><div className="workflow-text"><strong>Generate report</strong><span>Export the current analysis with method and limitations.</span></div><button className="icon-button" onClick={() => currentAnalysis ? makeReport() : go('molecule')}><ChevronRight size={16}/></button></div></div></div><div className="panel-card"><div className="panel-title-row"><div><h3>Recent analyses</h3><p>Latest saved molecule calculations</p></div><button className="link-button" onClick={() => go('history')}>View all <ArrowUpRight size={14}/></button></div>{history.length === 0 ? <EmptyState icon={Atom} title="No analyses yet" copy="Start with aspirin's example SMILES or enter another molecule."/> : <div className="recent-list">{history.slice(0,4).map(item => <button className="recent-item" key={item.id} onClick={() => openHistory(item)}><div className="recent-molecule"><Atom size={17}/></div><div className="recent-info"><strong>{item.molecule_name || 'Unnamed molecule'}</strong><span>{item.canonical_smiles}</span></div><div className="recent-date">{new Date(item.created_at).toLocaleDateString()}</div><ChevronRight size={15}/></button>)}</div>}</div></div>
          <div className="bottom-disclaimer"><ShieldAlert size={16}/><div><strong>Scientific integrity built in</strong><span>Keyword hints, chemical descriptors, docking, and model predictions are different kinds of evidence. The current version calculates RDKit descriptors only; docking, ADMET, and de novo molecular generation are not implemented.</span></div><button onClick={() => go('roadmap')}>View limitations</button></div>
        </>}

        {page === 'disease' && <>
          <SectionHeader eyebrow="DOCUMENT INTAKE" title="Disease report analyzer" subtitle="Upload a selectable-text research PDF. Chemora-AI extracts text and simple review hints; you confirm all scientific details." action={<span className="pill neutral"><FileText size={13}/> PDF only · 15 MB max</span>}/>
          <div className="two-column wide-left"><div className="panel-card"><div className="panel-title-row"><div><h3>Upload a research document</h3><p>Scientific paper, disease review, or target study</p></div><div className="upload-icon"><FilePlus2 size={19}/></div></div><label className={`dropzone ${pdfFile ? 'has-file' : ''}`}><input type="file" accept="application/pdf,.pdf" onChange={e => setPdfFile(e.target.files?.[0] || null)}/><span className="drop-icon"><UploadCloud size={23}/></span><strong>{pdfFile ? pdfFile.name : 'Drop your PDF here'}</strong><span>{pdfFile ? `${(pdfFile.size / (1024*1024)).toFixed(2)} MB · Ready to upload` : 'or click to browse files'}</span><small>PDF · up to 15 MB · text-based PDFs in this version</small></label><button className="button primary full" onClick={uploadPDF} disabled={uploadBusy || !pdfFile}>{uploadBusy ? <><LoaderCircle className="spin" size={16}/> Extracting text…</> : <><UploadCloud size={16}/> Upload and extract</>}</button><div className="inline-note"><CircleHelp size={14}/><span>Scanned PDFs need OCR. This starter build reports when no selectable text is available.</span></div></div><div className="panel-card tips-card"><div className="tip-mark"><Microscope size={20}/></div><h3>What happens after upload?</h3><div className="tip-list"><div><CheckCircle2 size={16}/><span>Text is extracted with page information.</span></div><div><CheckCircle2 size={16}/><span>Common disease keywords and uppercase terms are surfaced as hints.</span></div><div><CheckCircle2 size={16}/><span>You review and manually confirm the disease and potential targets.</span></div><div><CheckCircle2 size={16}/><span>The PDF is linked to later molecule analyses and reports.</span></div></div><div className="note-card"><ShieldAlert size={15}/><p>Keyword matching is not AI-based medical entity recognition and may produce false positives. Verify all entities against the uploaded document.</p></div></div></div>
          {currentDisease && <div className="panel-card result-panel"><div className="panel-title-row"><div><div className="eyebrow">EXTRACTION COMPLETE</div><h3>{currentDisease.filename}</h3><p>{currentDisease.page_count} pages · {currentDisease.text_characters} extracted characters · ID {currentDisease.id}</p></div><span className="pill success"><CheckCircle2 size={13}/> Text extracted</span></div><div className="extraction-layout"><div className="form-stack"><label className="field-label">Confirm disease name <span>Editable</span><input value={currentDisease.diseaseName || ''} onChange={e => setCurrentDisease(v => ({ ...v, diseaseName: e.target.value }))} placeholder={currentDisease.hints?.possible_disease_terms?.[0] || 'Enter disease name from your source'}/></label><label className="field-label">Potential targets / proteins <span>comma-separated</span><textarea value={currentDisease.targetText ?? (currentDisease.hints?.possible_gene_or_protein_symbols || []).join(', ')} onChange={e => setCurrentDisease(v => ({ ...v, targetText: e.target.value }))} placeholder="Enter target names and identifiers after reviewing the PDF" rows={4}/></label><button className="button primary" onClick={confirmDisease}><CheckCircle2 size={16}/> Save reviewed information</button><button className="button secondary" onClick={() => { setSelectedReport(currentDisease.id); go('molecule'); }}>Continue to molecular analysis <ArrowUpRight size={15}/></button></div><div className="extraction-preview"><div className="preview-label">RULE-BASED HINTS</div><div className="hint-block"><strong>Possible disease terms</strong>{(currentDisease.hints?.possible_disease_terms || []).length ? <div className="chip-row">{currentDisease.hints.possible_disease_terms.map(x => <span className="chip" key={x}>{x}</span>)}</div> : <span className="muted-small">No common keyword detected.</span>}</div><div className="hint-block"><strong>Possible uppercase symbols</strong>{(currentDisease.hints?.possible_gene_or_protein_symbols || []).length ? <div className="chip-row">{currentDisease.hints.possible_gene_or_protein_symbols.slice(0,12).map(x => <span className="chip" key={x}>{x}</span>)}</div> : <span className="muted-small">No candidate symbol found.</span>}</div><div className="hint-block"><strong>First-page excerpt</strong><p className="excerpt">{currentDisease.hints?.first_page_excerpt || currentDisease.text_preview}</p></div></div></div><div className="text-preview"><div className="preview-label">EXTRACTED TEXT PREVIEW</div><pre>{currentDisease.text_preview}</pre></div></div>}
          <div className="panel-card"><div className="panel-title-row"><div><h3>Uploaded document history</h3><p>Saved locally on this prototype environment</p></div><span className="pill neutral">{reports.length} documents</span></div>{reports.length === 0 ? <EmptyState icon={FileText} title="No documents uploaded" copy="Your disease research PDFs will appear here after extraction."/> : <div className="table-wrap"><table><thead><tr><th>Document</th><th>Pages</th><th>Disease confirmed</th><th>Uploaded</th><th></th></tr></thead><tbody>{reports.map(r => <tr key={r.id}><td><div className="file-cell"><span className="file-mini"><FileText size={15}/></span><div><strong>{r.filename}</strong><small>Report ID {r.id}</small></div></div></td><td>{r.page_count}</td><td>{r.confirmed_disease_name || <span className="muted-small">Pending review</span>}</td><td>{new Date(r.uploaded_at).toLocaleDateString()}</td><td><button className="small-button" onClick={async () => { const r2 = await api(`/disease-reports/${r.id}`); setCurrentDisease({ ...r2, diseaseName: r2.disease_name || '', targetText: (r2.targets || []).join(', ') }); setSelectedReport(r.id); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>Open</button></td></tr>)}</tbody></table></div>}</div>
        </>}

        {page === 'molecule' && <>
          <SectionHeader eyebrow="MOLECULAR TOOLKIT" title="Molecular analysis" subtitle="Calculate descriptors from a SMILES string with RDKit. Results are saved to local SQLite history." action={<span className="pill success"><StatusDot okay/> RDKit descriptors</span>}/>
          <div className="analysis-layout"><div className="panel-card analysis-form-card"><div className="panel-title-row"><div><h3>Input molecule</h3><p>Enter a chemical SMILES representation</p></div><div className="upload-icon"><Atom size={20}/></div></div><form onSubmit={analyzeMolecule}><label className="field-label">Molecule name <span>Optional</span><input value={moleculeName} onChange={e => setMoleculeName(e.target.value)} placeholder="e.g. Aspirin" maxLength={200}/></label><label className="field-label">SMILES string <span>Required</span><textarea className="smiles-input" value={smiles} onChange={e => setSmiles(e.target.value)} rows={4} placeholder="Enter SMILES notation" required/></label><div className="sample-actions"><button className="small-button" type="button" onClick={() => { setMoleculeName('Aspirin'); setSmiles(ASPIRIN_SMILES); }}>Load aspirin example</button><span className="muted-small">Sample compound for code validation</span></div><label className="field-label">Link a disease report <span>Optional</span><select value={selectedReport} onChange={e => setSelectedReport(e.target.value)}><option value="">No disease report linked</option>{reports.map(r => <option key={r.id} value={r.id}>{r.confirmed_disease_name ? `${r.confirmed_disease_name} — ` : ''}{r.filename}</option>)}</select></label><button className="button primary full" type="submit" disabled={analyzeBusy}>{analyzeBusy ? <><LoaderCircle className="spin" size={16}/> Calculating descriptors…</> : <><FlaskConical size={16}/> Analyze molecule</>}</button></form><div className="inline-note"><ShieldAlert size={14}/><span>This version does not calculate binding affinity or predict ADMET properties.</span></div></div>
          <div className="analysis-result-column">{currentAnalysis?.result ? <><div className="result-title-row"><div><div className="eyebrow">ANALYSIS RESULT · {currentAnalysis.id}</div><h2>{currentAnalysis.molecule_name || 'Unnamed molecule'}</h2><p>Calculated using RDKit molecular descriptors.</p></div><button className="button secondary" onClick={() => makeReport()} disabled={reportBusy}>{reportBusy ? <LoaderCircle className="spin" size={15}/> : <ArrowDownToLine size={15}/>} Export PDF</button></div><div className="molecule-result-card"><div className="molecule-sketch" dangerouslySetInnerHTML={{ __html: currentAnalysis.result.molecular_structure_svg || '' }}/><div className="molecule-meta"><span className="pill success"><CheckCircle2 size={12}/> Valid SMILES</span><div className="formula">{currentAnalysis.result.descriptors.molecular_formula}</div><div className="canonical-label">CANONICAL SMILES</div><code>{currentAnalysis.result.canonical_smiles}</code></div></div><div className="descriptor-grid">{[
            ['Molecular weight', `${currentAnalysis.result.descriptors.molecular_weight_da} Da`, 'Calculated'],
            ['LogP', currentAnalysis.result.descriptors.logp, 'Lipophilicity estimate'],
            ['H-bond donors', currentAnalysis.result.descriptors.h_bond_donors, 'Descriptor'],
            ['H-bond acceptors', currentAnalysis.result.descriptors.h_bond_acceptors, 'Descriptor'],
            ['Rotatable bonds', currentAnalysis.result.descriptors.rotatable_bonds, 'Flexibility'],
            ['TPSA', `${currentAnalysis.result.descriptors.tpsa_a2} Å²`, 'Polar surface area'],
          ].map(([label, value, hint]) => <div className="descriptor-card" key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>)}</div><div className="panel-card lipinski-card"><div className="panel-title-row"><div><h3>Lipinski Rule of Five</h3><p>A heuristic for common oral drug-like properties</p></div><span className={`pill ${currentAnalysis.result.lipinski.violations <= 1 ? 'success' : 'warning'}`}>{currentAnalysis.result.lipinski.violations} violations</span></div><div className="criteria-list">{currentAnalysis.result.lipinski.criteria.map(c => <div className="criterion-row" key={c.criterion}><span className={c.passed ? 'criterion-check pass' : 'criterion-check fail'}>{c.passed ? <CheckCircle2 size={14}/> : <XCircle size={14}/>}</span><span>{c.criterion}</span><strong className={c.passed ? 'pass-text' : 'fail-text'}>{c.passed ? 'Pass' : 'Violation'}</strong></div>)}</div><div className="science-disclaimer"><ShieldAlert size={15}/><p>{currentAnalysis.result.lipinski.interpretation}</p></div></div><div className="optional-row"><div><span className="optional-icon"><Network size={17}/></span><div><strong>Molecular docking</strong><p>Not configured in this starter build.</p></div></div><span className="pill neutral">Not performed</span></div><div className="optional-row"><div><span className="optional-icon"><Gauge size={17}/></span><div><strong>ADMET prediction</strong><p>No prediction model has been integrated.</p></div></div><span className="pill neutral">Not evaluated</span></div></> : <div className="panel-card blank-result"><div className="molecular-orb"><Atom size={48}/></div><h3>Your analysis will appear here</h3><p>Start with the included aspirin SMILES example. RDKit will validate the chemical representation and calculate molecular descriptors.</p><div className="blank-result-tags"><span><CheckCircle2 size={13}/> SMILES validation</span><span><CheckCircle2 size={13}/> Descriptor calculation</span><span><CheckCircle2 size={13}/> Lipinski screening</span></div></div>}</div></div>
        </>}

        {page === 'history' && <><SectionHeader eyebrow="SAVED WORK" title="Analysis history" subtitle="Review saved molecular calculations and reopen a result or export its report." action={<button className="button primary" onClick={() => go('molecule')}><Atom size={16}/> New analysis</button>}/><div className="panel-card">{history.length === 0 ? <EmptyState icon={Clock3} title="Your history is empty" copy="Molecule analyses are stored after a successful calculation."/> : <div className="table-wrap"><table><thead><tr><th>Molecule</th><th>SMILES</th><th>Disease report</th><th>Created</th><th>Actions</th></tr></thead><tbody>{history.map(item => <tr key={item.id}><td><div className="file-cell"><span className="molecule-mini"><Atom size={15}/></span><div><strong>{item.molecule_name || 'Unnamed molecule'}</strong><small>Analysis {item.id}</small></div></div></td><td><code className="table-code">{item.canonical_smiles}</code></td><td>{item.disease_filename || <span className="muted-small">Not linked</span>}</td><td>{new Date(item.created_at).toLocaleString()}</td><td><button className="small-button" onClick={() => openHistory(item)}>Open result</button></td></tr>)}</tbody></table></div>}</div></>}

        {page === 'reports' && <><SectionHeader eyebrow="EXPORTS" title="Generated reports" subtitle="PDF reports are created from saved molecular analyses. Each report states the methods used and work not performed." action={<button className="button primary" onClick={() => go('molecule')}><Atom size={16}/> New analysis</button>}/><div className="panel-card">{generatedReports.length === 0 ? <><EmptyState icon={FileCheck2} title="No reports generated yet" copy="Open Molecular Analysis, run a calculation, and use Export PDF. The generated file will appear here."/><div className="centered-actions"><button className="button primary" onClick={() => go('molecule')}>Open molecular analysis <ChevronRight size={15}/></button></div></> : <div className="table-wrap"><table><thead><tr><th>Report</th><th>Molecule</th><th>Analysis ID</th><th>Created</th><th></th></tr></thead><tbody>{generatedReports.map(r => <tr key={r.id}><td><div className="file-cell"><span className="file-mini"><FileCheck2 size={15}/></span><div><strong>{r.filename}</strong><small>Report ID {r.id}</small></div></div></td><td>{r.molecule_name || 'Unnamed molecule'}</td><td>{r.analysis_id}</td><td>{new Date(r.created_at).toLocaleString()}</td><td><a className="small-button download-link" href={`${API}/reports/${r.id}/download`}>Download</a></td></tr>)}</tbody></table></div>}</div></>}

        {page === 'roadmap' && <><SectionHeader eyebrow="CAPABILITIES & LIMITATIONS" title="Current build and next integrations" subtitle="This starter is deliberately transparent about which scientific operations actually run."/><div className="roadmap-grid"><div className="panel-card"><div className="roadmap-status done"><CheckCircle2 size={16}/> IMPLEMENTED IN THIS BUILD</div><h3>Working prototype</h3><ul className="roadmap-list"><li>PDF text extraction with page count and preview</li><li>Rule-based keyword hints for user review</li><li>RDKit SMILES parsing and molecular descriptors</li><li>Lipinski Rule of Five evaluation</li><li>SQLite history persistence</li><li>Downloadable analysis PDF</li><li>Basic API validation and error messages</li></ul></div><div className="panel-card"><div className="roadmap-status planned"><Clock3 size={16}/> FUTURE INTEGRATIONS</div><h3>Advanced drug discovery</h3><ul className="roadmap-list"><li>OCR for scanned research PDFs</li><li>Scientific NER / LLM extraction with source evidence</li><li>PubChem compound search</li><li>RCSB PDB target retrieval and structure preparation</li><li>AutoDock Vina molecular docking</li><li>Documented ADMET prediction model</li><li>Generative molecular proposal model</li><li>Authentication and cloud deployment</li></ul></div></div><div className="bottom-disclaimer"><ShieldAlert size={16}/><div><strong>Do not treat this as a validated drug discovery engine</strong><span>Current calculations describe molecular structure only. They do not prove disease relevance, target binding, novelty, safety, or therapeutic efficacy.</span></div></div><div className="panel-card"><div className="panel-title-row"><div><h3>System architecture</h3><p>Implemented path in this starter release</p></div></div><div className="architecture-flow"><div>Research PDF <small>Upload</small></div><ChevronRight/><div>PyMuPDF <small>Text extraction</small></div><ChevronRight/><div>Human review <small>Confirm context</small></div><ChevronRight/><div>RDKit <small>SMILES analysis</small></div><ChevronRight/><div>ReportLab <small>PDF export</small></div></div></div></>}
        <footer className="page-footer"><span>CHEMORA-AI · LOCAL RESEARCH PROTOTYPE</span><span>Built for learning · Validate every scientific claim</span></footer>
      </div>
    </main>
  </div>;
}
