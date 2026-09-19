import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { editorApi } from './api';
import BlockEditor from './BlockEditor';

export default function ReportEditorPage() {
  const { taskId } = useParams();
  const [params] = useSearchParams();
  const kind = params.get('file') || 'detailed';
  const run = params.get('run') || '';
  const [state, setState] = useState({});
  useEffect(() => {
    let cancelled = false; setState({});
    editorApi(taskId, kind, run).load().then(data => {
      if (!cancelled) setState({ data });
    }).catch(error => { if (!cancelled) setState({ error: error.message }); });
    return () => { cancelled = true; };
  }, [taskId, kind, run]);
  if (!state.data) return <div className="vd-page block-editor-loading" role="status">{state.error || '正在打开文档…'}{state.error && <Link to={`/report/${taskId}`}>返回报告</Link>}</div>;
  return <BlockEditor key={`${taskId}/${kind}/${state.data.output_dir}`} taskId={taskId} kind={kind} initial={state.data} />;
}
