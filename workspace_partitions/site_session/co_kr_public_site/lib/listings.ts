import { listingItems } from "@/components/sample-data";

export function getAllListings() {
  return listingItems;
}

export function getListingIds() {
  return listingItems.map((item) => item.id);
}

export function getListingById(id: string) {
  const decoded = decodeURIComponent(id);

  return listingItems.find((item) => item.id === decoded) ??
    listingItems.find((item) => item.id.toLowerCase() === decoded.toLowerCase());
}

export function getAdjacentListings(id: string) {
  const listing = getListingById(id);

  if (!listing) {
    return { previous: null, next: null };
  }

  const index = listingItems.findIndex((item) => item.id === listing.id);

  if (index === -1) {
    return { previous: null, next: null };
  }

  return {
    previous: index > 0 ? listingItems[index - 1] : null,
    next: index < listingItems.length - 1 ? listingItems[index + 1] : null,
  };
}

export function getLatestListingUpdatedAt() {
  return listingItems.reduce((latest, item) => (
    new Date(item.updatedAt).getTime() > new Date(latest).getTime() ? item.updatedAt : latest
  ), listingItems[0]?.updatedAt ?? new Date().toISOString());
}
