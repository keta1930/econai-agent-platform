import { useState, useCallback } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { useApi } from "@/hooks/useApi";
import { sharingApi } from "@/api/sharing";
import { ApiError } from "@/api/client";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { ThumbsUp, Send, Presentation } from "lucide-react";
import type { TopicListItem, TopicMaterialsResponse, TopicStatus } from "@/types/sharing";

const MAX_VOTES = 3;

const STATUS_LABELS: Record<TopicStatus, string> = {
  completed: "已分享",
  confirmed: "已确定",
  voting: "投票中",
};
const STATUS_VARIANTS: Record<TopicStatus, "default" | "secondary" | "outline"> = {
  completed: "default",
  confirmed: "secondary",
  voting: "outline",
};

type StatusFilter = "all" | TopicStatus;

// ---------------------------------------------------------------------------
// SuggestInput
// ---------------------------------------------------------------------------

function SuggestInput({ onSuggested }: { onSuggested: () => void }) {
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmed = title.trim();
    if (!trimmed) return;

    setSubmitting(true);
    try {
      await sharingApi.suggest({ title: trimmed });
      toast.success("主题已提交");
      setTitle("");
      onSuggested();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error("提交失败");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex gap-2">
      <Input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="输入你想分享的主题..."
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.nativeEvent.isComposing) {
            e.preventDefault();
            handleSubmit();
          }
        }}
      />
      <Button
        size="sm"
        disabled={!title.trim() || submitting}
        onClick={handleSubmit}
        className="shrink-0"
      >
        <Send className="mr-1.5 h-3.5 w-3.5" />
        推荐
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SharingPage (main)
// ---------------------------------------------------------------------------

export default function SharingPage() {
  const { data, loading, error, refetch } = useApi(() => sharingApi.list(), []);
  const [topicsOverride, setTopicsOverride] = useState<Map<string, { voted: boolean; count: number }>>(new Map());
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loadingVoteIds, setLoadingVoteIds] = useState<Set<string>>(new Set());

  // Materials sheet state
  const [sheetOpen, setSheetOpen] = useState(false);
  const [materials, setMaterials] = useState<TopicMaterialsResponse | null>(null);
  const [loadingMaterials, setLoadingMaterials] = useState(false);

  const allTopics = data?.items ?? [];
  const serverTotalVotes = data?.total_votes ?? 0;

  // Apply optimistic vote overrides
  const topics = allTopics.map((t) => {
    const override = topicsOverride.get(t.id);
    if (override) {
      return { ...t, current_user_voted: override.voted, vote_count: override.count };
    }
    return t;
  });

  const voteDelta = allTopics.reduce((delta, t) => {
    const override = topicsOverride.get(t.id);
    if (!override) return delta;
    const serverVoted = t.current_user_voted;
    if (override.voted && !serverVoted) return delta + 1;
    if (!override.voted && serverVoted) return delta - 1;
    return delta;
  }, 0);
  const totalVotes = serverTotalVotes + voteDelta;
  const atLimit = totalVotes >= MAX_VOTES;

  // Counts per status
  const countByStatus: Record<StatusFilter, number> = {
    all: topics.length,
    completed: topics.filter((t) => t.status === "completed").length,
    confirmed: topics.filter((t) => t.status === "confirmed").length,
    voting: topics.filter((t) => t.status === "voting").length,
  };

  // Filter + sort: completed → confirmed → voting, voting sorted by vote_count desc
  // 后端已按 completed → confirmed → voting(票数降序) 排好序
  // 不在前端重排，避免乐观更新时列表项跳动
  const filteredTopics = topics
    .filter((t) => statusFilter === "all" || t.status === statusFilter);

  const showVotingControls = statusFilter === "all" || statusFilter === "voting";

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleVoteChange = useCallback(
    (topicId: string, voted: boolean, newCount: number) => {
      setTopicsOverride((prev) => {
        const next = new Map(prev);
        next.set(topicId, { voted, count: newCount });
        return next;
      });
    },
    []
  );

  async function handleToggleVote(topic: TopicListItem) {
    if (loadingVoteIds.has(topic.id)) return;

    const snapshot = { voted: topic.current_user_voted, count: topic.vote_count };
    const optimisticCount = snapshot.voted ? snapshot.count - 1 : snapshot.count + 1;

    handleVoteChange(topic.id, !snapshot.voted, optimisticCount);
    setLoadingVoteIds((prev) => new Set(prev).add(topic.id));

    try {
      const res = snapshot.voted
        ? await sharingApi.unvote(topic.id)
        : await sharingApi.vote(topic.id);
      handleVoteChange(topic.id, !snapshot.voted, res.vote_count);
    } catch (err) {
      handleVoteChange(topic.id, snapshot.voted, snapshot.count);
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error("操作失败");
      }
    } finally {
      setLoadingVoteIds((prev) => {
        const next = new Set(prev);
        next.delete(topic.id);
        return next;
      });
    }
  }

  async function handleViewMaterials(topic: TopicListItem) {
    setSheetOpen(true);
    setMaterials(null);

    if (!topic.has_materials) return;

    setLoadingMaterials(true);
    try {
      const res = await sharingApi.getMaterials(topic.id);
      setMaterials(res);
    } catch {
      toast.error("加载素材失败");
    } finally {
      setLoadingMaterials(false);
    }
  }

  function handleRefresh() {
    setTopicsOverride(new Map());
    refetch();
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Header: title + nav + suggest */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-heading font-semibold page-title-decorated">
            课程分享
          </h1>
          <nav className="flex items-center gap-4">
            {(
              [
                ["all", "全部"],
                ["completed", "已分享"],
                ["confirmed", "已确定"],
                ["voting", "投票中"],
              ] as const
            ).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setStatusFilter(tab)}
                className={cn(
                  "relative pb-1 text-sm transition-colors",
                  statusFilter === tab
                    ? "font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {label}({countByStatus[tab]})
                {statusFilter === tab && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--gold)] rounded-full" />
                )}
              </button>
            ))}
          </nav>
        </div>

        {showVotingControls && countByStatus.voting > 0 && (
          <span className="text-sm text-muted-foreground shrink-0">
            已投 {totalVotes}/{MAX_VOTES}
          </span>
        )}
      </div>

      {/* Suggest input */}
      {showVotingControls && countByStatus.voting > 0 && (
        <SuggestInput onSuggested={handleRefresh} />
      )}

      {/* Topic table */}
      {filteredTopics.length === 0 ? (
        <EmptyState
          icon={<Presentation className="h-12 w-12" />}
          title="暂无主题"
          description="分享主题将在此展示"
        />
      ) : (
        <Table className="data-table">
          <TableHeader>
            <TableRow>
              <TableHead>标题</TableHead>
              <TableHead>来源</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>汇报人</TableHead>
              <TableHead>票数</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredTopics.map((topic) => {
              const isCompleted = topic.status === "completed";
              const isVoting = topic.status === "voting";
              const canVote = topic.current_user_voted || !atLimit;

              return (
                <TableRow
                  key={topic.id}
                  className={isCompleted && topic.has_materials ? "cursor-pointer" : undefined}
                  onClick={isCompleted && topic.has_materials ? () => handleViewMaterials(topic) : undefined}
                >
                  <TableCell className="font-medium">{topic.title}</TableCell>
                  <TableCell>
                    <Badge variant={topic.is_student_submitted ? "secondary" : "outline"} className="text-xs">
                      {topic.is_student_submitted ? "同学推荐" : "系统"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[topic.status]}>
                      {STATUS_LABELS[topic.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {topic.presenters ?? "-"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {topic.vote_count}
                  </TableCell>
                  <TableCell className="text-right">
                    {isVoting && (
                      <Button
                        size="sm"
                        variant={topic.current_user_voted ? "outline" : "default"}
                        disabled={loadingVoteIds.has(topic.id) || !canVote}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleVote(topic);
                        }}
                      >
                        <ThumbsUp className="mr-1.5 h-3.5 w-3.5" />
                        {topic.current_user_voted
                          ? "已投票"
                          : atLimit
                            ? "已达上限"
                            : "投票"}
                      </Button>
                    )}
                    {isCompleted && topic.has_materials && (
                      <span className="text-xs text-muted-foreground">查看素材</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {/* Materials sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>{materials?.title ?? "分享素材"}</SheetTitle>
          </SheetHeader>
          <div className="px-4 pb-4">
            {loadingMaterials ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            ) : materials ? (
              <MarkdownContent content={materials.materials_content} />
            ) : (
              <p className="text-sm text-muted-foreground">暂无素材</p>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
