export default function YangdoLoading() {
  return (
    <div className="page-loading" role="status" aria-label="양도가 산정 페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">AI 양도가 산정 엔진을 준비하고 있습니다</p>
    </div>
  );
}
