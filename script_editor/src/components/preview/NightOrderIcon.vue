<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { formatNightOrder } from "../../utils/nightOrders";
import {
  NIGHT_ICON_CENTER,
  NIGHT_ICON_FALLBACK_RADIUS,
  NIGHT_ICON_SIZE,
} from "./previewConfig";
import type { NightOrderItem } from "./previewTypes";

const props = defineProps<{ item: NightOrderItem }>();
const imageFailed = ref(false);
const fallbackVisible = computed(() => !props.item.image || imageFailed.value);
const fallbackLines = computed(() => {
  const chars = Array.from(props.item.name);
  return Array.from({ length: Math.ceil(chars.length / 2) }, (_, index) =>
    chars.slice(index * 2, index * 2 + 2).join(""),
  );
});
const fallbackFontSize = computed(() => Math.min(13, 28 / fallbackLines.value.length));
watch(() => props.item.image, () => { imageFailed.value = false; });
</script>

<template>
  <g data-night-icon>
    <title>{{ `${item.name} ${formatNightOrder(item.order)}${item.reminder ? `\n${item.reminder}` : ""}` }}</title>
    <g data-night-icon-fallback :style="{ display: fallbackVisible ? undefined : 'none' }">
      <circle
        :cx="NIGHT_ICON_CENTER"
        :cy="NIGHT_ICON_CENTER"
        :r="NIGHT_ICON_FALLBACK_RADIUS"
        fill="#f8fafc"
        :stroke="item.color"
        stroke-width="2"
      />
      <text
        class="svg-night-fallback"
        :font-size="fallbackFontSize"
        text-anchor="middle"
        dominant-baseline="central"
        :fill="item.color"
        font-weight="900"
      >
        <tspan
          v-for="(line, index) in fallbackLines"
          :key="index"
          :x="NIGHT_ICON_CENTER"
          :y="NIGHT_ICON_CENTER + (index - (fallbackLines.length - 1) / 2) * fallbackFontSize"
        >{{ line }}</tspan>
      </text>
    </g>
    <image
      v-if="item.image"
      :href="item.image"
      :width="NIGHT_ICON_SIZE"
      :height="NIGHT_ICON_SIZE"
      preserveAspectRatio="xMidYMid meet"
      @load="imageFailed = false"
      @error="imageFailed = true"
    />
  </g>
</template>
