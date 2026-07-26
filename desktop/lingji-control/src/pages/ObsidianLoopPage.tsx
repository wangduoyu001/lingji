import ObsidianOperations from "../components/ObsidianOperations";
import type { PageProps } from "../types";
import ObsidianPage from "./ObsidianPage";

export default function ObsidianLoopPage(props: PageProps) {
  return <div className="stack"><ObsidianPage {...props} /><ObsidianOperations api={props.api} active={props.active} /></div>;
}
