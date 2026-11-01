package com.ttit.myapp.activity;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import com.squareup.picasso.Picasso;
import com.ttit.myapp.R;

/**
 * 资讯详情页：展示标题、作者、时间、评论数和封面，
 * 并支持通过系统浏览器或头条 App 打开原文。
 */
public class NewsDetailActivity extends BaseActivity {

    private ImageView imgHeader;
    private ImageView imgThumb;
    private TextView tvTitle;
    private TextView tvAuthor;
    private TextView tvTime;
    private TextView tvComment;
    private TextView tvBody;

    @Override
    protected int initLayout() {
        return R.layout.activity_news_detail;
    }

    @Override
    protected void initView() {
        imgHeader = findViewById(R.id.img_header);
        imgThumb = findViewById(R.id.img_thumb);
        tvTitle = findViewById(R.id.tv_title);
        tvAuthor = findViewById(R.id.tv_author);
        tvTime = findViewById(R.id.tv_time);
        tvComment = findViewById(R.id.tv_comment);
        tvBody = findViewById(R.id.tv_body);
    }

    @Override
    protected void initData() {
        Bundle bundle = getIntent().getExtras();
        if (bundle == null) {
            finish();
            return;
        }

        String title = bundle.getString("title", "");
        String author = bundle.getString("author", "");
        String time = bundle.getString("time", "");
        String header = bundle.getString("header", "");
        String thumb = bundle.getString("thumb", "");
        String url = bundle.getString("url", "");
        int comment = bundle.getInt("comment", 0);

        tvTitle.setText(title);
        tvAuthor.setText(TextUtils.isEmpty(author) ? "未知作者" : author);
        tvTime.setText(time);
        tvComment.setText(comment + " 评论");

        tvBody.setText("这是 App 内置的资讯详情页。\n\n"
                + "标题：" + title + "\n"
                + "作者：" + author + "\n"
                + "发布时间：" + time + "\n\n"
                + "资讯内容来自今日头条热榜，点击下方“查看原文”可以打开完整内容。");

        if (!TextUtils.isEmpty(header)) {
            Picasso.with(this)
                    .load(header)
                    .into(imgHeader);
        } else {
            imgHeader.setVisibility(View.GONE);
        }

        if (!TextUtils.isEmpty(thumb)) {
            Picasso.with(this)
                    .load(thumb)
                    .into(imgThumb);
        } else {
            imgThumb.setVisibility(View.GONE);
        }

        findViewById(R.id.btn_back).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                finish();
            }
        });

        TextView btnOpen = findViewById(R.id.btn_open);
        if (!TextUtils.isEmpty(url)) {
            btnOpen.setVisibility(View.VISIBLE);
            btnOpen.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                    } catch (Exception e) {
                        showToast("无法打开原文链接");
                    }
                }
            });
        } else {
            btnOpen.setVisibility(View.GONE);
        }
    }
}
