import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { modelsApi } from "@/api/models";
import { toast } from "sonner";
import { Loader2, Plus, Trash2, Zap } from "lucide-react";
import { ConfirmDialog } from "@/components/confirm-dialog";
import type { ModelConfigCreateRequest } from "@/types/model";

export default function ModelsPage() {
  const { data, loading, error, refetch } = useApi(() => modelsApi.list(), []);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<ModelConfigCreateRequest>({
    name: "",
    api_key: "",
    base_url: "",
    adapter_type: "openai",
    supports_vision: false,
  });
  const [creating, setCreating] = useState(false);
  const [activatingId, setActivatingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const isFormValid = form.name.trim() && form.api_key.trim() && form.base_url.trim();

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await modelsApi.create({
        name: form.name.trim(),
        api_key: form.api_key.trim(),
        base_url: form.base_url.trim(),
        adapter_type: form.adapter_type,
        supports_vision: form.supports_vision,
      });
      toast.success("模型已添加");
      setDialogOpen(false);
      setForm({ name: "", api_key: "", base_url: "", adapter_type: "openai", supports_vision: false });
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "添加失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleActivate(modelId: string) {
    setActivatingId(modelId);
    try {
      const res = await modelsApi.activate(modelId);
      toast.success(res.message);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "激活失败");
    } finally {
      setActivatingId(null);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await modelsApi.delete(deleteTarget.id);
      toast.success("模型已删除");
      setDeleteTarget(null);
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  const models = data?.items ?? [];

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-heading font-semibold page-title-decorated">模型管理</h1>
          <span className="text-sm text-muted-foreground">共 {models.length} 个模型配置</span>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>
            <Plus className="mr-2 h-4 w-4" />
            添加模型
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>添加模型</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="model-name">名称</Label>
                <Input
                  id="model-name"
                  placeholder="例如 gpt-4o"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model-key">API Key</Label>
                <Input
                  id="model-key"
                  type="password"
                  placeholder="请输入 API Key"
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model-url">Base URL</Label>
                <Input
                  id="model-url"
                  placeholder="例如 https://api.openai.com/v1"
                  value={form.base_url}
                  onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>调用格式类型</Label>
                <Select
                  value={form.adapter_type}
                  onValueChange={(v) => setForm({ ...form, adapter_type: v as "openai" | "anthropic" })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={form.supports_vision ?? false}
                  onCheckedChange={(checked) => setForm({ ...form, supports_vision: checked })}
                />
                <Label className="cursor-pointer text-sm font-normal">
                  支持图片输入（VLM）
                </Label>
              </div>
              <DialogFooter>
                <DialogClose render={<Button type="button" variant="outline" />}>
                  取消
                </DialogClose>
                <Button type="submit" disabled={!isFormValid || creating}>
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  添加
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Table className="data-table">
        <TableHeader>
          <TableRow>
            <TableHead>名称</TableHead>
            <TableHead>Base URL</TableHead>
            <TableHead>类型</TableHead>
            <TableHead>图片</TableHead>
            <TableHead>状态</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {models.map((model) => (
            <TableRow key={model.id}>
              <TableCell className="font-medium">{model.name}</TableCell>
              <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                {model.base_url}
              </TableCell>
              <TableCell>
                <Badge variant="outline">{model.adapter_type}</Badge>
              </TableCell>
              <TableCell>
                {model.supports_vision ? (
                  <Badge className="bg-[var(--cyan-mid)]/10 text-[var(--cyan-mid)] hover:bg-[var(--cyan-mid)]/10">
                    VLM
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell>
                {model.is_active ? (
                  <Badge className="bg-success/10 text-success hover:bg-success/10">
                    活跃
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="bg-secondary text-muted-foreground hover:bg-secondary">
                    未激活
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right space-x-2">
                {!model.is_active && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={activatingId === model.id}
                      onClick={() => handleActivate(model.id)}
                    >
                      {activatingId === model.id ? (
                        <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                      ) : (
                        <Zap className="mr-1 h-4 w-4" />
                      )}
                      设为活跃
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-[var(--danger)] hover:text-[var(--danger)] hover:bg-[var(--danger)]/10"
                      onClick={() => setDeleteTarget({ id: model.id, name: model.name })}
                    >
                      <Trash2 className="mr-1 h-4 w-4" />
                      删除
                    </Button>
                  </>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="删除模型"
        description={`确定要删除模型「${deleteTarget?.name ?? ""}」吗？此操作不可恢复。`}
        onConfirm={handleDelete}
        confirmText="删除"
        variant="destructive"
        loading={deleting}
      />
    </div>
  );
}
