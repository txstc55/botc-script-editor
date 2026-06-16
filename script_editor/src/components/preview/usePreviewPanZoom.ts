import { computed, nextTick, onBeforeUnmount, onMounted, ref, type ComputedRef } from "vue";
import {
  PREVIEW_BASE_WIDTH,
  PREVIEW_CANVAS_BOTTOM_SAFE_SPACE,
  PREVIEW_CANVAS_TOP_PADDING,
  PREVIEW_MAX_ZOOM,
  PREVIEW_MIN_ZOOM,
  PREVIEW_PAN_SETTLE_EPSILON,
  PREVIEW_WHEEL_ZOOM_SPEED,
  PREVIEW_ZOOM_SETTLE_EPSILON,
  PREVIEW_ZOOM_SMOOTHING,
  SVG_WIDTH,
} from "./previewConfig";
import type { PreviewPanGesture, SvgPreviewLayout } from "./previewTypes";

export function usePreviewPanZoom(previewLayout: ComputedRef<SvgPreviewLayout>) {
  const previewStage = ref<HTMLElement | null>(null);
  const previewZoom = ref(1);
  const previewPan = ref({ x: 0, y: PREVIEW_CANVAS_TOP_PADDING });
  const targetPreviewZoom = ref(1);
  const targetPreviewPan = ref({ x: 0, y: PREVIEW_CANVAS_TOP_PADDING });
  const previewPanGesture = ref<PreviewPanGesture | null>(null);
  const isPreviewPanning = computed(() => Boolean(previewPanGesture.value));
  const previewDisplayHeight = computed(() => PREVIEW_BASE_WIDTH * previewLayout.value.height / SVG_WIDTH);
  const previewCanvasStyle = computed(() => ({
    width: `${PREVIEW_BASE_WIDTH}px`,
    height: `${previewDisplayHeight.value + PREVIEW_CANVAS_BOTTOM_SAFE_SPACE}px`,
    transform: `matrix(${previewZoom.value}, 0, 0, ${previewZoom.value}, ${previewPan.value.x}, ${previewPan.value.y})`,
  }));
  let previewResizeObserver: ResizeObserver | null = null;
  let zoomAnimationFrame: number | null = null;
  let lastStageWidth = 0;
  let hasCenteredPreview = false;

  onMounted(() => {
    previewResizeObserver = new ResizeObserver(() => handlePreviewStageResize());
    if (previewStage.value) {
      previewResizeObserver.observe(previewStage.value);
    }
    nextTick(() => centerPreviewCanvas({ force: true }));
  });

  onBeforeUnmount(() => {
    previewResizeObserver?.disconnect();
    cancelZoomAnimation();
  });

  function handlePreviewWheel(event: WheelEvent) {
    if (!previewStage.value) {
      return;
    }
    const rect = previewStage.value.getBoundingClientRect();
    const cursorX = event.clientX - rect.left;
    const cursorY = event.clientY - rect.top;
    const oldZoom = targetPreviewZoom.value;
    const oldPan = targetPreviewPan.value;
    const zoomFactor = Math.exp(-event.deltaY * PREVIEW_WHEEL_ZOOM_SPEED);
    const nextZoom = clamp(oldZoom * zoomFactor, PREVIEW_MIN_ZOOM, PREVIEW_MAX_ZOOM);
    if (nextZoom === oldZoom) {
      return;
    }

    targetPreviewPan.value = {
      x: cursorX - ((cursorX - oldPan.x) / oldZoom) * nextZoom,
      y: cursorY - ((cursorY - oldPan.y) / oldZoom) * nextZoom,
    };
    targetPreviewZoom.value = nextZoom;
    startSmoothZoom();
  }

  function handlePreviewPointerDown(event: PointerEvent) {
    if (event.button !== 1) {
      return;
    }
    event.preventDefault();
    cancelZoomAnimation();
    targetPreviewZoom.value = previewZoom.value;
    targetPreviewPan.value = previewPan.value;
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
    const nextPan = {
      x: gesture.startPanX + event.clientX - gesture.startX,
      y: gesture.startPanY + event.clientY - gesture.startY,
    };
    previewPan.value = nextPan;
    targetPreviewPan.value = nextPan;
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

  function handlePreviewStageResize() {
    const stage = previewStage.value;
    if (!stage || previewPanGesture.value) {
      return;
    }
    const rect = stage.getBoundingClientRect();
    if (!hasCenteredPreview) {
      lastStageWidth = rect.width;
      centerPreviewCanvas({ force: true });
      return;
    }
    if (Math.abs(rect.width - lastStageWidth) < 1) {
      return;
    }

    const widthDelta = rect.width - lastStageWidth;
    lastStageWidth = rect.width;
    const nextPan = {
      x: previewPan.value.x + widthDelta / 2,
      y: previewPan.value.y,
    };
    previewPan.value = nextPan;
    targetPreviewPan.value = nextPan;
    targetPreviewZoom.value = previewZoom.value;
  }

  function centerPreviewCanvas({ force = false } = {}) {
    const stage = previewStage.value;
    if (!stage || previewPanGesture.value || (hasCenteredPreview && !force)) {
      return;
    }
    cancelZoomAnimation();
    const rect = stage.getBoundingClientRect();
    lastStageWidth = rect.width;
    const nextPan = {
      x: (rect.width - PREVIEW_BASE_WIDTH * previewZoom.value) / 2,
      y: PREVIEW_CANVAS_TOP_PADDING,
    };
    previewPan.value = nextPan;
    targetPreviewPan.value = nextPan;
    targetPreviewZoom.value = previewZoom.value;
    hasCenteredPreview = true;
  }

  function startSmoothZoom() {
    if (zoomAnimationFrame !== null) {
      return;
    }
    zoomAnimationFrame = requestAnimationFrame(stepSmoothZoom);
  }

  function stepSmoothZoom() {
    zoomAnimationFrame = null;
    const nextZoom = lerp(previewZoom.value, targetPreviewZoom.value, PREVIEW_ZOOM_SMOOTHING);
    const nextPan = {
      x: lerp(previewPan.value.x, targetPreviewPan.value.x, PREVIEW_ZOOM_SMOOTHING),
      y: lerp(previewPan.value.y, targetPreviewPan.value.y, PREVIEW_ZOOM_SMOOTHING),
    };
    const zoomSettled = Math.abs(nextZoom - targetPreviewZoom.value) < PREVIEW_ZOOM_SETTLE_EPSILON;
    const panSettled =
      Math.abs(nextPan.x - targetPreviewPan.value.x) < PREVIEW_PAN_SETTLE_EPSILON &&
      Math.abs(nextPan.y - targetPreviewPan.value.y) < PREVIEW_PAN_SETTLE_EPSILON;

    if (zoomSettled && panSettled) {
      previewZoom.value = targetPreviewZoom.value;
      previewPan.value = targetPreviewPan.value;
      return;
    }

    previewZoom.value = nextZoom;
    previewPan.value = nextPan;
    startSmoothZoom();
  }

  function cancelZoomAnimation() {
    if (zoomAnimationFrame === null) {
      return;
    }
    cancelAnimationFrame(zoomAnimationFrame);
    zoomAnimationFrame = null;
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

function lerp(start: number, end: number, amount: number) {
  return start + (end - start) * amount;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
