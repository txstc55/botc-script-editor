import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComputedRef } from "vue";
import {
  PREVIEW_BASE_WIDTH,
  PREVIEW_CANVAS_BOTTOM_SAFE_SPACE,
  PREVIEW_CANVAS_TOP_PADDING,
  PREVIEW_MAX_ZOOM,
  PREVIEW_MIN_ZOOM,
  PREVIEW_WHEEL_ZOOM_SPEED,
  SVG_WIDTH,
} from "./previewConfig";
import type { PreviewPanGesture, SvgPreviewLayout } from "./previewTypes";

export function usePreviewPanZoom(previewLayout: ComputedRef<SvgPreviewLayout>) {
  const previewStage = ref<HTMLElement | null>(null);
  const previewZoom = ref(1);
  const previewPan = ref({ x: 0, y: PREVIEW_CANVAS_TOP_PADDING });
  const previewPanGesture = ref<PreviewPanGesture | null>(null);
  const isPreviewPanning = computed(() => Boolean(previewPanGesture.value));
  const previewDisplayHeight = computed(() => PREVIEW_BASE_WIDTH * previewLayout.value.height / SVG_WIDTH);
  const previewCanvasStyle = computed(() => ({
    width: `${PREVIEW_BASE_WIDTH}px`,
    height: `${previewDisplayHeight.value + PREVIEW_CANVAS_BOTTOM_SAFE_SPACE}px`,
    transform: `matrix(${previewZoom.value}, 0, 0, ${previewZoom.value}, ${previewPan.value.x}, ${previewPan.value.y})`,
  }));
  let previewResizeObserver: ResizeObserver | null = null;

  onMounted(() => {
    previewResizeObserver = new ResizeObserver(() => centerPreviewCanvas());
    if (previewStage.value) {
      previewResizeObserver.observe(previewStage.value);
    }
    nextTick(centerPreviewCanvas);
  });

  onBeforeUnmount(() => {
    previewResizeObserver?.disconnect();
  });

  watch(() => previewLayout.value.height, () => {
    nextTick(centerPreviewCanvas);
  });

  function handlePreviewWheel(event: WheelEvent) {
    if (!previewStage.value) {
      return;
    }
    const rect = previewStage.value.getBoundingClientRect();
    const cursorX = event.clientX - rect.left;
    const cursorY = event.clientY - rect.top;
    const oldZoom = previewZoom.value;
    const zoomFactor = Math.exp(-event.deltaY * PREVIEW_WHEEL_ZOOM_SPEED);
    const nextZoom = clamp(oldZoom * zoomFactor, PREVIEW_MIN_ZOOM, PREVIEW_MAX_ZOOM);
    if (nextZoom === oldZoom) {
      return;
    }

    previewPan.value = {
      x: cursorX - ((cursorX - previewPan.value.x) / oldZoom) * nextZoom,
      y: cursorY - ((cursorY - previewPan.value.y) / oldZoom) * nextZoom,
    };
    previewZoom.value = nextZoom;
  }

  function handlePreviewPointerDown(event: PointerEvent) {
    if (event.button !== 1) {
      return;
    }
    event.preventDefault();
    try {
      previewStage.value?.setPointerCapture(event.pointerId);
    } catch {
      // Synthetic pointer events do not always have an active pointer capture target.
    }
    previewPanGesture.value = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPanX: previewPan.value.x,
      startPanY: previewPan.value.y,
    };
  }

  function handlePreviewPointerMove(event: PointerEvent) {
    const gesture = previewPanGesture.value;
    if (!gesture || gesture.pointerId !== event.pointerId) {
      return;
    }
    event.preventDefault();
    previewPan.value = {
      x: gesture.startPanX + event.clientX - gesture.startX,
      y: gesture.startPanY + event.clientY - gesture.startY,
    };
  }

  function handlePreviewPointerUp(event: PointerEvent) {
    if (previewPanGesture.value?.pointerId !== event.pointerId) {
      return;
    }
    try {
      previewStage.value?.releasePointerCapture(event.pointerId);
    } catch {
      // The pointer may already be released by the browser.
    }
    previewPanGesture.value = null;
  }

  function centerPreviewCanvas() {
    const stage = previewStage.value;
    if (!stage || previewPanGesture.value) {
      return;
    }
    const rect = stage.getBoundingClientRect();
    previewPan.value = {
      x: (rect.width - PREVIEW_BASE_WIDTH * previewZoom.value) / 2,
      y: PREVIEW_CANVAS_TOP_PADDING,
    };
  }

  return {
    previewStage,
    previewCanvasStyle,
    isPreviewPanning,
    handlePreviewWheel,
    handlePreviewPointerDown,
    handlePreviewPointerMove,
    handlePreviewPointerUp,
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
