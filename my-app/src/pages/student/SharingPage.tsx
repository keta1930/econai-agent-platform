import { useState, useCallback } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
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
import { toast } from "sonner";
import { ThumbsUp, BookOpen, CheckCircle2, Vote, Send } from "lucide-react";
import type { TopicListItem, TopicMaterialsResponse } from "@/types/sharing";

const MAX_VOTES = 3;

// ---------------------------------------------------------------------------
// CompletedTab
// ---------------------------------------------------------------------------

function CompletedTab({ topics }: { topics: TopicListItem[] }) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [materials, setMaterials] = useState<TopicMaterialsResponse | null>(null);
  const [loadingMaterials, setLoadingMaterials] = useState(false);

  async function handleViewMaterials(topic: TopicListItem) {
    setSheetOpen(true);
    setMaterials(null);

    if (!topic.has_materials) {
      return;
    }

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

  if (topics.length === 0) {
    return (
      <EmptyState
        icon={<BookOpen className="h-12 w-12" />}
        title="暂无已分享内容"
        description="已完成的分享内容将在此展示"
      />
    );
  }

  return (
    <>
      <div className="rounded-lg border divide-y">
        {topics.map((topic) => (
          <div
            key={topic.id}
            className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-accent/50 transition-colors"
            onClick={() => handleViewMaterials(topic)}
          >
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium truncate">{topic.title}</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {topic.presenters && <span>{topic.presenters}</span>}
                {topic.session_number != null && (
                  <span className="ml-2">第 {topic.session_number} 次分享</span>
                )}
                {topic.shared_at && (
                  <span className="ml-2">
                    {new Date(topic.shared_at).toLocaleDateString("zh-CN")}
                  </span>
                )}
              </p>
            </div>
            {topic.has_materials && (
              <BookOpen className="ml-3 h-4 w-4 shrink-0 text-muted-foreground" />
            )}
          </div>
        ))}
      </div>

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
    </>
  );
}

// ---------------------------------------------------------------------------
// ConfirmedTab
// ---------------------------------------------------------------------------

function ConfirmedTab({ topics }: { topics: TopicListItem[] }) {
  if (topics.length === 0) {
    return (
      <EmptyState
        icon={<CheckCircle2 className="h-12 w-12" />}
        title="暂无已确定主题"
        description="已确定的未来分享主题将在此展示"
      />
    );
  }

  return (
    <div className="rounded-lg border divide-y">
      {topics.map((topic) => (
        <div key={topic.id} className="px-4 py-3">
          <span className="text-sm font-medium">{topic.title}</span>
        </div>
      ))}
    </div>
  );
}

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
// VotingTab
// ---------------------------------------------------------------------------

function VotingTab({
  topics,
  totalVotes,
  onVoteChange,
  onRefresh,
}: {
  topics: TopicListItem[];
  totalVotes: number;
  onVoteChange: (topicId: number, voted: boolean, newCount: number) => void;
  onRefresh: () => void;
}) {
  const [loadingIds, setLoadingIds] = useState<Set<number>>(new Set());
  const atLimit = totalVotes >= MAX_VOTES;

  async function handleToggleVote(topic: TopicListItem) {
    if (loadingIds.has(topic.id)) return;

    // Snapshot before optimistic update for reliable rollback
    const snapshot = { voted: topic.current_user_voted, count: topic.vote_count };
    const optimisticCount = snapshot.voted ? snapshot.count - 1 : snapshot.count + 1;

    onVoteChange(topic.id, !snapshot.voted, optimisticCount);
    setLoadingIds((prev) => new Set(prev).add(topic.id));

    try {
      const res = snapshot.voted
        ? await sharingApi.unvote(topic.id)
        : await sharingApi.vote(topic.id);
      onVoteChange(topic.id, !snapshot.voted, res.vote_count);
    } catch (err) {
      onVoteChange(topic.id, snapshot.voted, snapshot.count);
      if (err instanceof ApiError) {
        toast.error(err.message);
      } else {
        toast.error("操作失败");
      }
    } finally {
      setLoadingIds((prev) => {
        const next = new Set(prev);
        next.delete(topic.id);
        return next;
      });
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          已投 {totalVotes}/{MAX_VOTES}
        </p>
      </div>

      <SuggestInput onSuggested={onRefresh} />

      {topics.length === 0 ? (
        <EmptyState
          icon={<Vote className="h-12 w-12" />}
          title="暂无投票主题"
          description="候选的分享主题将在此展示"
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {topics.map((topic) => {
            const canVote = topic.current_user_voted || !atLimit;
            return (
              <Card key={topic.id}>
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <h3 className="text-sm font-medium truncate">{topic.title}</h3>
                      {topic.is_student_submitted && (
                        <Badge variant="secondary" className="shrink-0 text-xs">
                          同学推荐
                        </Badge>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {topic.vote_count} 票
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant={topic.current_user_voted ? "outline" : "default"}
                    disabled={loadingIds.has(topic.id) || !canVote}
                    onClick={() => handleToggleVote(topic)}
                    className="ml-3 shrink-0"
                  >
                    <ThumbsUp className="mr-1.5 h-3.5 w-3.5" />
                    {topic.current_user_voted
                      ? "已投票"
                      : atLimit
                        ? "已达上限"
                        : "投票"}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SharingPage (main)
// ---------------------------------------------------------------------------

export default function SharingPage() {
  const { data, loading, error, refetch } = useApi(() => sharingApi.list(), []);
  const [topicsOverride, setTopicsOverride] = useState<Map<number, { voted: boolean; count: number }>>(new Map());

  const allTopics = data?.items ?? [];
  const serverTotalVotes = data?.total_votes ?? 0;

  // Apply optimistic overrides
  const topics = allTopics.map((t) => {
    const override = topicsOverride.get(t.id);
    if (override) {
      return { ...t, current_user_voted: override.voted, vote_count: override.count };
    }
    return t;
  });

  // Compute total votes: server total + delta from overrides
  const voteDelta = allTopics.reduce((delta, t) => {
    const override = topicsOverride.get(t.id);
    if (!override) return delta;
    const serverVoted = t.current_user_voted;
    if (override.voted && !serverVoted) return delta + 1;
    if (!override.voted && serverVoted) return delta - 1;
    return delta;
  }, 0);
  const totalVotes = serverTotalVotes + voteDelta;

  const completed = topics.filter((t) => t.status === "completed");
  const confirmed = topics.filter((t) => t.status === "confirmed");
  const voting = topics
    .filter((t) => t.status === "voting")
    .sort((a, b) => b.vote_count - a.vote_count);

  const handleVoteChange = useCallback(
    (topicId: number, voted: boolean, newCount: number) => {
      setTopicsOverride((prev) => {
        const next = new Map(prev);
        next.set(topicId, { voted, count: newCount });
        return next;
      });
    },
    []
  );

  function handleRefresh() {
    setTopicsOverride(new Map());
    refetch();
  }

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
      <h1 className="text-2xl font-heading font-semibold">课程分享</h1>
      <Tabs defaultValue="completed">
        <TabsList>
          <TabsTrigger value="completed">已分享</TabsTrigger>
          <TabsTrigger value="confirmed">已确定</TabsTrigger>
          <TabsTrigger value="voting">投票</TabsTrigger>
        </TabsList>
        <TabsContent value="completed">
          <CompletedTab topics={completed} />
        </TabsContent>
        <TabsContent value="confirmed">
          <ConfirmedTab topics={confirmed} />
        </TabsContent>
        <TabsContent value="voting">
          <VotingTab
            topics={voting}
            totalVotes={totalVotes}
            onVoteChange={handleVoteChange}
            onRefresh={handleRefresh}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
