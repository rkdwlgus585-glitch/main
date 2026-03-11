export default function ConsultLoading() {
  return (
    <div className="page-loading" role="status" aria-label="고객센터 페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">고객센터 정보를 불러오고 있습니다</p>
    </div>
  );
}
