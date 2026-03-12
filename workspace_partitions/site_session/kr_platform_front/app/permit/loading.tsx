export default function PermitLoading() {
  return (
    <div className="page-loading" role="status" aria-label="AI 인허가 검토 페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">AI 인허가 검토 엔진을 준비하고 있습니다</p>
    </div>
  );
}
