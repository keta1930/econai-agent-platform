import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { useClassContext } from "@/contexts/ClassContext";
import { adminSharingApi } from "@/api/sharing";
import { toast } from "sonner";
import { PlusCircle, Pencil, Trash2, Presentation } from "lucide-react";
import type {
  AdminTopicListItem,
  TopicStatus,
  TopicCreateRequest,
  TopicUpdateRequest,
} from "@/types/sharing";

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

// ---------------------------------------------------------------------------
// TopicEditSheet
// ---------------------------------------------------------------------------

interface EditSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  topic: AdminTopicListItem | null;
  classId: number;
  onSaved: () => void;
}

function TopicEditSheet({ open, onOpenChange, topic, classId, onSaved }: EditSheetProps) {
  const isCreate = !topic;
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<TopicStatus>("voting");
  const [presenters, setPresenters] = useState("");
  const [sessionNumber, setSessionNumber] = useState("");
  const [sharedAt, setSharedAt] = useState("");
  const [materialsContent, setMaterialsContent] = useState("");

  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen && topic) {
      setTitle(topic.title);
      setStatus(topic.status);
      setPresenters(topic.presenters ?? "");
      setSessionNumber(topic.session_number?.toString() ?? "");
      setSharedAt(topic.shared_at ? topic.shared_at.slice(0, 10) : "");
      setMaterialsContent(topic.materials_content ?? "");
    } else if (nextOpen && !topic) {
      setTitle("");
      setStatus("voting");
      setPresenters("");
      setSessionNumber("");
      setSharedAt("");
      setMaterialsContent("");
    }
    onOpenChange(nextOpen);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      toast.error("请输入标题");
      return;
    }

    setSaving(true);
    try {
      if (isCreate) {
        const data: TopicCreateRequest = {
          title: title.trim(),
          class_id: classId,
          status,
          ...(status === "completed" && {
            presenters: presenters.trim() || undefined,
            session_number: sessionNumber ? parseInt(sessionNumber) : undefined,
            shared_at: sharedAt || undefined,
            materials_content: materialsContent || undefined,
          }),
        };
        await adminSharingApi.create(data);
        toast.success("主题已创建");
      } else {
        const data: TopicUpdateRequest = {
          title: title.trim(),
          status,
          presenters: status === "completed" ? presenters.trim() || null : null,
          session_number: status === "completed" && sessionNumber ? parseInt(sessionNumber) : null,
          shared_at: status === "completed" && sharedAt ? sharedAt : null,
          materials_content: status === "completed" ? materialsContent || null : null,
        };
        await adminSharingApi.update(topic.id, data);
        toast.success("主题已更新");
      }
      onOpenChange(false);
      onSaved();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "操作失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="sm:max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isCreate ? "创建主题" : "编辑主题"}</SheetTitle>
        </SheetHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-4 pb-4">
          <div className="space-y-2">
            <Label htmlFor="topic-title">标题</Label>
            <Input
              id="topic-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入主题标题"
            />
          </div>

          <div className="space-y-2">
            <Label>状态</Label>
            <Select value={status} onValueChange={(v) => setStatus(v as TopicStatus)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="voting">投票中</SelectItem>
                <SelectItem value="confirmed">已确定</SelectItem>
                <SelectItem value="completed">已分享</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {status === "completed" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="topic-presenters">汇报人</Label>
                <Input
                  id="topic-presenters"
                  value={presenters}
                  onChange={(e) => setPresenters(e.target.value)}
                  placeholder="汇报人姓名，多人用 & 连接"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="topic-session">分享次数</Label>
                <Input
                  id="topic-session"
                  type="number"
                  min={1}
                  value={sessionNumber}
                  onChange={(e) => setSessionNumber(e.target.value)}
                  placeholder="第几次分享"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="topic-date">分享时间</Label>
                <Input
                  id="topic-date"
                  type="date"
                  value={sharedAt}
                  onChange={(e) => setSharedAt(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="topic-materials">素材内容 (Markdown)</Label>
                <Textarea
                  id="topic-materials"
                  value={materialsContent}
                  onChange={(e) => setMaterialsContent(e.target.value)}
                  placeholder="粘贴 Markdown 素材内容"
                  className="min-h-[200px] font-mono text-sm"
                />
              </div>
            </>
          )}

          <SheetFooter>
            <Button type="submit" disabled={saving} className="w-full">
              {saving ? "保存中..." : "保存"}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}

// ---------------------------------------------------------------------------
// SharingManagePage
// ---------------------------------------------------------------------------

export default function SharingManagePage() {
  const navigate = useNavigate();
  const { currentClass } = useClassContext();
  const classId = currentClass?.id;

  const { data, loading, error, refetch } = useApi(
    () => (classId ? adminSharingApi.list(undefined, classId) : Promise.resolve({ items: [] })),
    [classId],
  );
  const [editTopic, setEditTopic] = useState<AdminTopicListItem | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminTopicListItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  if (!currentClass) {
    return (
      <EmptyState
        icon={<Presentation className="h-12 w-12" />}
        title="请先选择班级"
        description="在左侧导航栏选择一个班级，或先创建班级"
        action={
          <Button onClick={() => navigate("/admin/classes")}>
            <PlusCircle className="mr-2 h-4 w-4" />
            前往班级管理
          </Button>
        }
      />
    );
  }

  const allTopics = data?.items ?? [];
  const filteredTopics =
    statusFilter === "all"
      ? allTopics
      : allTopics.filter((t) => t.status === statusFilter);

  function handleCreate() {
    setEditTopic(null);
    setEditOpen(true);
  }

  function handleEdit(topic: AdminTopicListItem) {
    setEditTopic(topic);
    setEditOpen(true);
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await adminSharingApi.delete(deleteTarget.id);
      toast.success("主题已删除");
      setDeleteTarget(null);
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-28" />
        </div>
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold">分享管理</h1>
        <Button onClick={handleCreate}>
          <PlusCircle className="mr-2 h-4 w-4" />
          创建主题
        </Button>
      </div>

      <Tabs defaultValue="all" onValueChange={setStatusFilter}>
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="completed">已分享</TabsTrigger>
          <TabsTrigger value="confirmed">已确定</TabsTrigger>
          <TabsTrigger value="voting">投票中</TabsTrigger>
        </TabsList>

        <TabsContent value={statusFilter}>
          {filteredTopics.length === 0 ? (
            <EmptyState
              icon={<Presentation className="h-12 w-12" />}
              title="暂无主题"
              description="点击「创建主题」添加第一个分享主题"
            />
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标题</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>汇报人</TableHead>
                    <TableHead>分享次数</TableHead>
                    <TableHead>票数</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTopics.map((topic) => (
                    <TableRow key={topic.id}>
                      <TableCell className="font-medium">{topic.title}</TableCell>
                      <TableCell>
                        {topic.is_student_submitted ? (
                          <Badge variant="secondary" className="text-xs">同学推荐</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">系统</span>
                        )}
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
                        {topic.session_number != null ? `第 ${topic.session_number} 次` : "-"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {topic.vote_count}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => handleEdit(topic)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="text-muted-foreground hover:text-destructive"
                            onClick={() => setDeleteTarget(topic)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>
      </Tabs>

      <TopicEditSheet
        open={editOpen}
        onOpenChange={setEditOpen}
        topic={editTopic}
        classId={classId!}
        onSaved={refetch}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="删除主题"
        description={`确定要删除主题「${deleteTarget?.title}」吗？关联的投票记录将被一并删除，此操作不可撤销。`}
        confirmText="删除"
        onConfirm={handleDelete}
        loading={deleting}
      />
    </div>
  );
}
