<?php
/**
 * Plugin Name: GNSS Bridge
 * Description: Minimal REST bridge exposing WPML's official translation-linking
 *              hooks and the Yoast SEO meta fields to the external GNSS AI
 *              Translation Engine. Deliberately contains zero translation
 *              logic — that lives entirely in the external Python engine
 *              (see ROADMAP.md FASE 0, "App externa vs. plugin WordPress
 *              tot en un", MEMORIA.md 2026-07-23).
 * Version:     0.1.0
 */

if (!defined('ABSPATH')) {
    exit;
}

const GNSS_BRIDGE_NAMESPACE = 'gnss-bridge/v1';

/**
 * Capability required to call any gnss-bridge endpoint. Matches the
 * dedicated `translation_bot` account design (ROADMAP.md FASE 1): Editor
 * role, never Administrator.
 */
function gnss_bridge_permission_check(): bool {
    return current_user_can('edit_posts');
}

add_action('rest_api_init', 'gnss_bridge_register_routes');

function gnss_bridge_register_routes(): void {
    register_rest_route(GNSS_BRIDGE_NAMESPACE, '/link-translation', [
        'methods'             => 'POST',
        'callback'            => 'gnss_bridge_link_translation',
        'permission_callback' => 'gnss_bridge_permission_check',
        'args'                => [
            'element_id'           => ['required' => true, 'type' => 'integer'],
            'trid'                 => ['required' => true, 'type' => 'integer'],
            'language_code'        => ['required' => true, 'type' => 'string'],
            'source_language_code' => ['required' => true, 'type' => 'string'],
        ],
    ]);

    register_rest_route(GNSS_BRIDGE_NAMESPACE, '/translation-status/(?P<post_id>\d+)', [
        'methods'             => 'GET',
        'callback'            => 'gnss_bridge_translation_status',
        'permission_callback' => 'gnss_bridge_permission_check',
        'args'                => [
            'post_id'       => ['required' => true, 'type' => 'integer'],
            'language_code' => ['required' => false, 'type' => 'string'],
        ],
    ]);

    // Job/XLIFF path (ROADMAP.md FASE 1 addendum, BIBLIOGRAFIA.md §11).
    // Deliberately NOT implemented: WPML's own job/XLIFF REST namespace
    // (wpml/tm/v1) turned out to reject Application-Password auth even for
    // a full Administrator (confirmed empirically 2026-08-05, MEMORIA.md),
    // and the underlying PHP class/method names are undocumented. Guessing
    // at them here would be reckless on a production site — this file loads
    // on every single request (mu-plugin), so one wrong class name is a
    // fatal error that takes the whole site down, English content included.
    // These routes fail loudly and safely (501) until PLA-ACCIO.md task 1.8
    // is resolved through a proper source review or a WPML support ticket.
    foreach ([['POST', '/create-job'], ['GET', '/export-xliff/(?P<job_id>\d+)'], ['POST', '/import-xliff']] as [$method, $route]) {
        register_rest_route(GNSS_BRIDGE_NAMESPACE, $route, [
            'methods'             => $method,
            'callback'            => 'gnss_bridge_not_implemented',
            'permission_callback' => 'gnss_bridge_permission_check',
        ]);
    }
}

function gnss_bridge_not_implemented(): WP_Error {
    return new WP_Error(
        'gnss_bridge_not_implemented',
        'The job/XLIFF write path is not implemented yet — see PLA-ACCIO.md task 1.8.',
        ['status' => 501]
    );
}

/**
 * Wraps WPML's official 3-step hook pattern for linking a translation to
 * its original (BIBLIOGRAFIA.md §2). Never touches the database directly.
 */
function gnss_bridge_link_translation(WP_REST_Request $request) {
    $element_id           = (int) $request->get_param('element_id');
    $trid                 = (int) $request->get_param('trid');
    $language_code        = sanitize_text_field((string) $request->get_param('language_code'));
    $source_language_code = sanitize_text_field((string) $request->get_param('source_language_code'));

    $post = get_post($element_id);
    if (!$post) {
        return new WP_Error(
            'gnss_bridge_invalid_element',
            "No post found with id {$element_id}.",
            ['status' => 404]
        );
    }

    $wpml_element_type = apply_filters('wpml_element_type', $post->post_type);

    do_action('wpml_set_element_language_details', [
        'element_id'           => $element_id,
        'element_type'         => $wpml_element_type,
        'trid'                 => $trid,
        'language_code'        => $language_code,
        'source_language_code' => $source_language_code,
    ]);

    return rest_ensure_response([
        'status'        => 'linked',
        'element_id'    => $element_id,
        'trid'          => $trid,
        'language_code' => $language_code,
    ]);
}

/**
 * Read-only: reports WPML's trid/language info for a post, and — when
 * `language_code` is passed — whether a translation already exists for
 * that target language.
 *
 * Uses the modern `wpml_object_id` filter, not the legacy `icl_object_id`
 * alias — the legacy one is documented to not reliably honor
 * `$return_original_if_missing = false` in every context, which is exactly
 * the false-positive bug found empirically 2026-08-05 (see MEMORIA.md):
 * `icl_object_id` returned the original post's own id as "the translation"
 * even for a nonsense language code.
 */
function gnss_bridge_translation_status(WP_REST_Request $request) {
    $post_id = (int) $request->get_param('post_id');

    $post = get_post($post_id);
    if (!$post) {
        return new WP_Error(
            'gnss_bridge_invalid_element',
            "No post found with id {$post_id}.",
            ['status' => 404]
        );
    }

    $language_details = apply_filters('wpml_element_language_details', null, [
        'element_id'   => $post_id,
        'element_type' => $post->post_type,
    ]);

    $response = [
        'element_id'    => $post_id,
        'trid'          => $language_details->trid ?? null,
        'language_code' => $language_details->language_code ?? null,
    ];

    $target_language = $request->get_param('language_code');
    if ($target_language) {
        $target_language = sanitize_text_field((string) $target_language);
        $translated_id = apply_filters('wpml_object_id', $post_id, $post->post_type, false, $target_language);
        $response['translation_exists']  = (bool) $translated_id && $translated_id !== $post_id;
        $response['translated_post_id']  = ($translated_id && $translated_id !== $post_id) ? $translated_id : null;
    }

    return rest_ensure_response($response);
}

/**
 * Registers the Yoast SEO meta fields for REST read/write. Yoast does not
 * expose these individually via REST by default (confirmed empirically
 * against staging — AUDITORIA-INICIAL.md §0.5, MAPEIG-CAMPS.md §2).
 */
add_action('init', 'gnss_bridge_register_yoast_meta');

function gnss_bridge_register_yoast_meta(): void {
    $fields = ['_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_focuskw'];

    foreach (['post', 'page'] as $post_type) {
        foreach ($fields as $field) {
            register_post_meta($post_type, $field, [
                'show_in_rest'  => true,
                'single'        => true,
                'type'          => 'string',
                'auth_callback' => 'gnss_bridge_permission_check',
            ]);
        }
    }
}

/**
 * Registers Elementor's own layout meta fields for REST read/write.
 * `_elementor_data` is not exposed via REST by default (confirmed empirically
 * — AUDITORIA-INICIAL.md §0.5) even though it holds the page's real content
 * tree; `post_content` is only a secondary rendered copy Elementor keeps in
 * sync, editing it alone does not change the page's actual layout.
 * `_elementor_css` is deliberately NOT registered here — its generated CSS
 * is driven by widget IDs/style settings, which translation never changes,
 * so the original page's CSS file remains valid for a translated copy and
 * does not need to be duplicated.
 *
 * Hooked on 'rest_api_init' (not 'init'): registering on priority 20 of
 * 'init' still wasn't enough to make these keys appear in REST output
 * (confirmed empirically 2026-08-06 — the schema showed them registered,
 * but actual GET responses never included them, on any page, regardless
 * of size). Elementor likely re-registers them again specifically for REST
 * on 'rest_api_init', which fires after all 'init' callbacks — hooking
 * there too, at a late priority, is required for ours to be the one that
 * sticks. register_post_meta() is last-call-wins for a given
 * (post_type, meta_key) pair.
 */
add_action('init', 'gnss_bridge_register_elementor_meta', 20);
add_action('rest_api_init', 'gnss_bridge_register_elementor_meta', 20);

function gnss_bridge_register_elementor_meta(): void {
    $fields = ['_elementor_data', '_elementor_edit_mode', '_elementor_template_type', '_elementor_version'];

    foreach (['post', 'page'] as $post_type) {
        foreach ($fields as $field) {
            register_post_meta($post_type, $field, [
                'show_in_rest'  => true,
                'single'        => true,
                'type'          => 'string',
                'auth_callback' => 'gnss_bridge_permission_check',
            ]);
        }
    }
}
