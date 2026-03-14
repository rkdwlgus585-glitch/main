export default function YangdoLoading() {
  return (
    <div className="page-loading" role="status" aria-label="페이지 로딩 중">
      <div className="loading-spinner" />
      <p className="loading-text">페이지를 불러오고 있습니다</p>
    </div>
  );
}
