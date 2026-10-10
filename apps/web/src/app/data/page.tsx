import { LocalDataWorkspace } from "@/components/local-data-workspace";

export const metadata = {
  title: "Data and offline tools",
  description: "Browser-local backup, restore, and offline learning controls.",
};

export default function LocalDataPage() {
  return <main className="page-shell"><LocalDataWorkspace /></main>;
}
