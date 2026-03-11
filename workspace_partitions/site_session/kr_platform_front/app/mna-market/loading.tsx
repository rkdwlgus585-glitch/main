export default function MnaMarketLoading() {
  return (
    <div className="page-loading" role="status" aria-label="실시간 매물 페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">매물 정보를 불러오고 있습니다</p>
    </div>
  );
}
